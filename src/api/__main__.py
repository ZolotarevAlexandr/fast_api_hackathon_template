import os
import sys

from src.prepare import BASE_DIR, prepare

os.chdir(BASE_DIR)
if not os.getenv("SKIP_PREPARE"):
    prepare()

import uvicorn  # noqa: E402

# Get arguments from command
args = sys.argv[1:]
extended_args = [
    "src.api.app:app",
    "--use-colors",
    "--proxy-headers",
    "--forwarded-allow-ips=*",
    *args,
]

print(f"🚀 Starting Uvicorn server: 'uvicorn {' '.join(extended_args)}'")
uvicorn.main.main(extended_args)
