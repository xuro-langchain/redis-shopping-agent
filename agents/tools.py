import ast
from datetime import datetime
from typing import Optional

from langchain.tools import tool, ToolRuntime
from langchain_openai import OpenAIEmbeddings
from redisvl.query import VectorQuery, FilterQuery
from redisvl.query.filter import Tag, Num

from agents.utils import db, get_concert_index

# ------------------------------------------------------------
# Music Catalog Subagent Tools
# ------------------------------------------------------------

@tool
def get_albums_by_artist(artist: str):
    """Get albums by an artist."""
    return db.run(
        f"""
        SELECT Album.Title, Artist.Name 
        FROM Album 
        JOIN Artist ON Album.ArtistId = Artist.ArtistId 
        WHERE Artist.Name LIKE '%{artist}%';
        """,
        include_columns=True
    )

@tool
def get_tracks_by_artist(artist: str):
    """Get songs by an artist (or similar artists)."""
    return db.run(
        f"""
        SELECT Track.Name as SongName, Artist.Name as ArtistName 
        FROM Album 
        LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId 
        LEFT JOIN Track ON Track.AlbumId = Album.AlbumId 
        WHERE Artist.Name LIKE '%{artist}%';
        """,
        include_columns=True
    )

@tool
def get_songs_by_genre(genre: str):
    """
    Fetch songs from the database that match a specific genre.
    
    Args:
        genre (str): The genre of the songs to fetch.
    
    Returns:
        list[dict]: A list of songs that match the specified genre.
    """
    genre_id_query = f"SELECT GenreId FROM Genre WHERE Name LIKE '%{genre}%'"
    genre_ids = db.run(genre_id_query)
    if not genre_ids:
        return f"No songs found for the genre: {genre}"
    genre_ids = ast.literal_eval(genre_ids)
    genre_id_list = ", ".join(str(gid[0]) for gid in genre_ids)

    songs_query = f"""
        SELECT Track.Name as SongName, Artist.Name as ArtistName
        FROM Track
        LEFT JOIN Album ON Track.AlbumId = Album.AlbumId
        LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId
        WHERE Track.GenreId IN ({genre_id_list})
        GROUP BY Artist.Name
        LIMIT 8;
    """
    songs = db.run(songs_query, include_columns=True)
    if not songs:
        return f"No songs found for the genre: {genre}"
    formatted_songs = ast.literal_eval(songs)
    return [
        {"Song": song["SongName"], "Artist": song["ArtistName"]}
        for song in formatted_songs
    ]

@tool
def check_for_songs(song_title):
    """Check if a song exists by its name."""
    return db.run(
        f"""
        SELECT * FROM Track WHERE Name LIKE '%{song_title}%';
        """,
        include_columns=True
    )

music_tools = [get_albums_by_artist, get_tracks_by_artist, get_songs_by_genre, check_for_songs]

# ------------------------------------------------------------
# Opensearch E-commerce Agent Tools
# ------------------------------------------------------------

# TODO: Add Opensearch MCP tools

# ------------------------------------------------------------
# Invoice Subagent Tools
# ------------------------------------------------------------
@tool 
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list[dict]:
    """
    Look up all invoices for a customer using their ID, the customer ID is in a state variable, so you will not see it in the message history.
    The invoices are sorted in descending order by invoice date, which helps when the customer wants to view their most recent/oldest invoice, or if 
    they want to view invoices within a specific date range.
    
    Returns:
        list[dict]: A list of invoices for the customer.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    return db.run(f"SELECT * FROM Invoice WHERE CustomerId = {customer_id} ORDER BY InvoiceDate DESC;")


@tool 
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list[dict]:
    """
    Use this tool when the customer wants to know the details of one of their invoices based on the unit price/cost of the invoice.
    This tool looks up all invoices for a customer, and sorts the unit price from highest to lowest. In order to find the invoice associated with the customer, 
    we need to know the customer ID. The customer ID is in a state variable, so you will not see it in the message history.

    Returns:
        list[dict]: A list of invoices sorted by unit price.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    query = f"""
        SELECT Invoice.*, InvoiceLine.UnitPrice
        FROM Invoice
        JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
        WHERE Invoice.CustomerId = {customer_id}
        ORDER BY InvoiceLine.UnitPrice DESC;
    """
    customer_id = runtime.state.get("customer_id", {})
    return db.run(query)


@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """
    This tool will take in an invoice ID and a customer ID and return the employee information associated with the invoice.
    The customer ID is in a state variable, so you will not see it in the message history.
    Args:
        invoice_id (int): The ID of the specific invoice.

    Returns:
        dict: Information about the employee associated with the invoice.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    query = f"""
        SELECT Employee.FirstName, Employee.Title, Employee.Email
        FROM Employee
        JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
        JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
        WHERE Invoice.InvoiceId = ({invoice_id}) AND Invoice.CustomerId = ({customer_id});
    """
    
    employee_info = db.run(query, include_columns=True)
    
    if not employee_info:
        return f"No employee found for invoice ID {invoice_id} and customer identifier {customer_id}."
    return employee_info

invoice_tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price, get_employee_by_invoice_and_customer]


# ------------------------------------------------------------
# Concert Subagent Tools
# ------------------------------------------------------------

# Embedding model for query vectorization
_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


@tool
def recommend_concerts(
    query: Optional[str] = None,
    artist: Optional[str] = None,
    genres: Optional[list[str]] = None,
    location: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 5
) -> list[dict]:
    """
    Find concert recommendations using hybrid search (semantic + filters).
    
    Args:
        query: Natural language description of what you're looking for 
               (e.g., "energetic rock show", "chill jazz night", "outdoor summer festival")
        artist: Filter by specific artist name
        genres: Filter by genre tags (e.g., ["rock", "blues"])
        location: Filter by city/location (e.g., "New York, NY", "Austin, TX")
        max_price: Maximum ticket price
        limit: Maximum number of results to return (default 5)
    
    Returns:
        List of matching concerts with details including artist, venue, date, prices, etc.
    """
    # Log the search parameters
    print(f"[Concert Tool] Searching with:")
    print(f"  query: {query}")
    print(f"  artist: {artist}")
    print(f"  genres: {genres}")
    print(f"  location: {location}")
    print(f"  max_price: {max_price}")
    
    # Build filter expression
    filters = []
    
    # Genre filter
    if genres:
        filters.append(Tag("genre") == genres)
    
    # Location filter - extract city name (TAG fields split on commas)
    if location:
        city = location.split(",")[0].strip()
        filters.append(Tag("location") == city)
    
    # Price filter
    if max_price:
        filters.append(Num("price_min") <= max_price)
    
    # Only available tickets
    filters.append(Tag("tickets_available") == "true")
    
    # Combine filters
    filter_expression = None
    if filters:
        filter_expression = filters[0]
        for f in filters[1:]:
            filter_expression = filter_expression & f
    
    # Get the concert index
    index = get_concert_index()
    
    # Return fields for results
    return_fields = [
        "id", "name", "artist", "genre", "description", "venue", 
        "location", "date", "time", "price_min", "price_max", 
        "tickets_available", "age_restriction"
    ]
    
    # Build and execute query
    if query or artist:
        # Hybrid search: vector similarity + filters
        search_text = query or artist
        query_embedding = _embeddings.embed_query(search_text)
        
        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            filter_expression=filter_expression,
            return_fields=return_fields,
            num_results=limit
        )
        results = index.query(vector_query)
    else:
        # Filter-only search (when no semantic query provided)
        # Use a simple filter query
        filter_query = FilterQuery(
            filter_expression=filter_expression,
            return_fields=return_fields,
            num_results=limit
        )
        results = index.query(filter_query)
    
    # Format results
    formatted_results = []
    for r in results:
        # Convert price strings to floats for formatting
        price_min = float(r.get('price_min', 0) or 0)
        price_max = float(r.get('price_max', 0) or 0)
        
        concert = {
            "id": r.get("id"),
            "name": r.get("name"),
            "artist": r.get("artist"),
            "genre": r.get("genre"),
            "venue": r.get("venue"),
            "location": r.get("location"),
            "price_range": f"${price_min:.0f} - ${price_max:.0f}",
            "tickets_available": r.get("tickets_available"),
            "age_restriction": r.get("age_restriction"),
            "description": r.get("description"),
        }
        formatted_results.append(concert)
    
    print(f"[Concert Tool] Found {len(formatted_results)} concerts")
    
    if not formatted_results:
        return [{"message": "No concerts found matching your criteria. Try broadening your search."}]
    
    return formatted_results


concert_tools = [recommend_concerts]

