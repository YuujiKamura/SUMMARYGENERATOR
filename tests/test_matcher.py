import unittest
from data.matcher import match_record_to_roles

def make_record(criteria, match):
    return {'criteria': criteria, 'match': match}

class TestMatcher(unittest.TestCase):
    def test_match_digit(self):
        record = make_record(['a', 'b', 'c'], '2')
        roles = ['a', 'b', 'x']
        result, found = match_record_to_roles(record, roles)
        print(f"[test_match_digit] roles={roles}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertTrue(result)
        self.assertSetEqual(set(found), {'a', 'b'})
        result, found = match_record_to_roles(record, ['a'])
        print(f"[test_match_digit] roles={['a']}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertFalse(result)
        self.assertEqual(found, ['a'])

    def test_match_any(self):
        record = make_record(['a', 'b'], 'any')
        roles = ['b', 'x']
        result, found = match_record_to_roles(record, roles)
        print(f"[test_match_any] roles={roles}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertTrue(result)
        self.assertEqual(found, ['b'])
        result, found = match_record_to_roles(record, ['x'])
        print(f"[test_match_any] roles={['x']}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertFalse(result)
        self.assertEqual(found, [])

    def test_match_all(self):
        record = make_record(['a', 'b'], 'all')
        roles = ['a', 'b', 'c']
        result, found = match_record_to_roles(record, roles)
        print(f"[test_match_all] roles={roles}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertTrue(result)
        self.assertSetEqual(set(found), {'a', 'b'})
        result, found = match_record_to_roles(record, ['a'])
        print(f"[test_match_all] roles={['a']}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertFalse(result)
        self.assertEqual(found, ['a'])

    def test_match_invalid(self):
        record = make_record(['a'], 'zzz')
        roles = ['a']
        result, found = match_record_to_roles(record, roles)
        print(f"[test_match_invalid] roles={roles}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertFalse(result)
        self.assertEqual(found, ['a'])

    def test_empty_criteria(self):
        record = make_record([], 'any')
        roles = ['a']
        result, found = match_record_to_roles(record, roles)
        print(f"[test_empty_criteria] roles={roles}, criteria={record['criteria']}, match={record['match']} -> result={result}, found={found}")
        self.assertFalse(result)
        self.assertEqual(found, [])

if __name__ == '__main__':
    unittest.main()
