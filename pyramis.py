import getopt
import sys
import webbrowser
from http.server import ThreadingHTTPServer

from server.handler import HTTPHandler


def main(name: str, argv: list[str]):
    port = 8041
    host = '127.0.0.1'

    try:
        opts, args = getopt.getopt(argv, "?h:p:", ["host=", "port="])
    except getopt.GetoptError:
        print(name + ' -h <host> -p <port>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-?':
            print(name + ' -h <host> -p <port>')
            sys.exit()
        elif opt in ("-h", "--host"):
            host = host
        elif opt in ("-p", "--port"):
            port = int(arg)

    print(f"Starting server on http://{host}:{port}")
    httpd = ThreadingHTTPServer(("", port), HTTPHandler)
    webbrowser.open_new_tab(f"http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main(sys.argv[0], sys.argv[1:])
