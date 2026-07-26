from src.storage import client
# from storage import client # for 目前调试
from supabase import Client
from postgrest.exceptions import APIError

class AuthServiceError(Exception): pass


def signup(username: str, password: str) -> str | None:
    try:
        existing = ( # Ensure the user name is unique
            client.table("user")
            .select("id")
            .eq("name", username)
            .execute()
        ) 
        
    except APIError as e:
        raise AuthServiceError("API Error") from e

    except Exception as e:
        raise AuthServiceError("Fail to retrieve data") from e
    
    if existing.data:
        return None # No a unique user name
        
    try:    
        response = (
            client.table("user")
            .insert(
                {
                    "name": username, 
                    "password": password
                }
            )
            .execute()
        )
        return response.data[0]["id"] # type: ignore[index]
    
    except APIError as e:
        if e.code == "23505": # For repeated users in High Concurrency Scenario
            return None # Same practice for repeated users
        
        raise AuthServiceError("Fail to access the database") from e
    
    except Exception as e:
        raise AuthServiceError("Fail to create new user") from e
    
    
def signin(username: str, password: str) -> str | None:
    try:
        validate = (
            client.table("user")
            .select("id")
            .eq("password", password)
            .eq("name", username)
            .execute()
        )
        
    except APIError as e:
        raise AuthServiceError("Fail to access the database") from e
    
    except Exception as e:
        raise AuthServiceError("Fail to retrieve user's information") from e
    
    if validate.data:
        return validate.data[0]["id"] # type: ignore[index]
    
    return None


def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    
    if not any(c.isupper() for c in password):
        return False
    
    if not any(c.islower() for c in password):
        return False
    
    if not any(c.isdigit() for c in password):
        return False
    
    return True