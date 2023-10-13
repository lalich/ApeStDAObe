from flask import Flask
from flask import request
from moralis import auth
from flask_cors import CORS

mma = Flask(__name__)
CORS(mma)

api_key = "QercoCAZywTkeKevoZC08gBJjPLRd7xN6aV88RZ5asiMv9r3tk762Hrj7pMEw6zE"

@mma.route('/requestChallenge', methods=["GET"])
def reqChallenge():
    args = request.args
    body = {
        "domain": "localhost:3000",
        "chainID": args.get("chainId"),
        "address": args.get("address"),
        "statement": "Welcome to ApeSt DAO",
        "uri": "https://localhost:3000",
        "expirationTime": "2024-01-01T00:00:00:000Z",
        "notBefore": "2023-01-01T00:00:00:000Z",
        "resources": ["https://docs.moralis.io/"],
        "timeout": 30,
    }

    result = auth.challenge.request_challenge_evm(
        api_key=api_key,
        body=body,
    )

    return result

@mma.route('/verifyChallenge', methods=["GET"])
def verifyChallenge():
    args = request.args
    body={
        "message": args.get("message"),
        "signature": args.get("signature"),
    }

    result = auth.challenge.verify_challenge_evm(
        api_key=api_key,
        body=body
    )

    return result

if __name__ == "__main__":
    mma.run(host="127.0.0.1", port=3000, debug=True)