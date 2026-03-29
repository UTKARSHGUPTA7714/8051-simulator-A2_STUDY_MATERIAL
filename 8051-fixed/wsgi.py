import sys, os

# Use bundled rich stub if the real package is absent
try:
    import rich
except ModuleNotFoundError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rich_stub"))

from api.index import app

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
