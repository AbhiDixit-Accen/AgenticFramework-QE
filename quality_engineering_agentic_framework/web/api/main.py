from .endpoints import app

# this is needed only for local run & Render webservice autocheck
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
