
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json

DB_PATH = Path(r"C:\FindArt\bwa.db")


def get_database_info():
    if not DB_PATH.exists():
        raise FileNotFoundError("Nie znaleziono bwa.db")

    sha256 = hashlib.sha256()

    with open(DB_PATH, "rb") as database:
        for chunk in iter(lambda: database.read(8192), b""):
            sha256.update(chunk)

    return {
        "version": sha256.hexdigest(),
        "size": DB_PATH.stat().st_size
    }


class FindArtHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/api/version":
            info = get_database_info()

            response = json.dumps(info).encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.send_header(
                "Content-Length",
                str(len(response))
            )
            self.end_headers()
            self.wfile.write(response)

        elif self.path == "/api/database":

            if not DB_PATH.exists():
                self.send_error(404, "Database not found")
                return

            size = DB_PATH.stat().st_size

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/vnd.sqlite3"
            )
            self.send_header(
                "Content-Length",
                str(size)
            )
            self.send_header(
                "Content-Disposition",
                'attachment; filename="bwa.db"'
            )
            self.end_headers()

            with open(DB_PATH, "rb") as database:
                while chunk := database.read(8192):
                    self.wfile.write(chunk)

        else:
            self.send_error(404, "Endpoint not found")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8001), FindArtHandler)
    print("FindArt server started!")
    print("Address: http://0.0.0.0:8001")
    server.serve_forever()