from langchain.sql_database import SQLDatabase

# Example for SQLite
db = SQLDatabase.from_uri("sqlite:///your_db_file.db")