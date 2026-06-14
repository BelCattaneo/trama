import bcrypt

# Cost factor 12 balances bcrypt's brute-force resistance against signup/login latency.
ROUNDS = 12


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=ROUNDS)).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
