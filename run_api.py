from uvicorn import run

if __name__ == "__main__":

    run("api:app", host="127.0.0.1", port=7000, reload=True)