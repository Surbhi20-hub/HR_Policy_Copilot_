"""Tiny test: embed one sentence and print how long the vector is."""
from src.config import get_embeddings


def main() -> None:
    """Turn one sentence into numbers and show the size."""
    sentence = "How many leaves do I get in a year?"
    vector: list[float] = get_embeddings().embed_query(sentence)
    print(f"Sentence : {sentence}")
    print(f"Vector length : {len(vector)}")
    print(f"First 5 numbers: {[round(x, 4) for x in vector[:5]]}")


if __name__ == "__main__":
    main()