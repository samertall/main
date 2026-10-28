"""Run a local, offline UI/agent demo without AWS credentials."""
import argparse
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from .handler import dispatch


class Handler(BaseHTTPRequestHandler):
    def serve(self):
        parsed=urlsplit(self.path)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size>18000:
                self.send_error(413,"Message too large")
                return
            payload=self.rfile.read(size).decode("utf-8") if size else ""
            result=dispatch(self.command,parsed.path,dict(self.headers),payload,parse_qs(parsed.query))
        except Exception:
            self.send_error(500,"Internal server error")
            return
        self.send_response(result["statusCode"])
        for key,val in result.get("headers",{}).items():self.send_header(key,val)
        self.end_headers()
        self.wfile.write(result["body"].encode("utf-8"))

    def do_GET(self):self.serve()
    def do_POST(self):self.serve()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--port",type=int,default=8787)
    p.add_argument("--host",default="127.0.0.1")
    args=p.parse_args()
    os.environ["APP_MODE"]="demo"
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f"ParentBridge AI DEMO (no AWS traffic): http://{args.host}:{args.port}",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass


if __name__=="__main__":main()
