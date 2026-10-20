import unittest

from src.trie import RadixTrie


class RadixTrieTests(unittest.TestCase):
    def test_prefix_matches_full_and_partial_compressed_edges(self) -> None:
        trie: RadixTrie[str] = RadixTrie()
        trie.insert("ezs42abc", "first")
        trie.insert("ezs42def", "second")
        trie.insert("ezs43abc", "third")

        self.assertCountEqual(trie.search_prefix("ezs42"), ["first", "second"])
        self.assertCountEqual(trie.search_prefix("ezs42a"), ["first"])
        self.assertCountEqual(trie.search_prefix("ezs43abc"), ["third"])
        self.assertEqual(trie.search_prefix("ezs44"), [])

    def test_duplicate_keys_and_clear(self) -> None:
        trie: RadixTrie[int] = RadixTrie()
        trie.insert("abc", 1)
        trie.insert("abc", 2)
        self.assertEqual(trie.search_prefix("abc"), [1, 2])
        self.assertEqual(len(trie), 2)

        trie.clear()
        self.assertEqual(len(trie), 0)
        self.assertEqual(trie.search_prefix("a"), [])

    def test_empty_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RadixTrie[int]().insert("", 1)


if __name__ == "__main__":
    unittest.main()
