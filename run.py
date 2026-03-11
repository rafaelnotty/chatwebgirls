import uvicorn

if __name__ == "__main__":
    # Arrancamos el servidor en el puerto 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)