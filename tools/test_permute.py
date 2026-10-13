"""The variant searcher's source handling: bodies survive parsing, rewrites give the intended forms."""
import random
import unittest

import permute as P

BODY = '''{
    Vector2& l = borders.second;
    l = leftRight;
    l = {l.x * inverseX * unknown4, l.y * inverseX * unknown4};
    if (flags & 0x200) { std::swap(a.x, a.w); } else count += 2;
    for (int i = 0; i < 4; ++i) c[i] *= scale;
    while (p != end) { ++p; }
}'''


def tree(text=BODY):
    return P.parse_stmt(P.tokens_of(text), 0)[0]


class Always:
    """A random generator stand-in that takes the first choice everywhere."""
    def choice(self, items):
        return items[0]

    def randrange(self, n):
        return 0

    def random(self):
        return 0.0


class Parsing(unittest.TestCase):
    def test_round_trip_keeps_every_token(self):
        self.assertEqual(P.render(tree()), P.tokens_of(BODY))

    def test_statement_kinds(self):
        self.assertEqual([s[0] for s in tree()[1]], ['simple', 'simple', 'simple', 'if', 'for', 'while'])

    def test_text_is_parsed_back_the_same(self):
        tokens = P.render(tree())
        self.assertEqual(P.tokens_of(P.text_of(tokens)), tokens)

    def test_atoms(self):
        t = P.tokens_of('a.b->c(1, 2)[3] + (x)')
        self.assertEqual(P.atom_at(t, 0), t.index('+'))
        self.assertEqual(P.atom_before(t, t.index('+')), 0)
        self.assertIsNone(P.atom_at(P.tokens_of('return x'), 0))


class Rewrites(unittest.TestCase):
    def test_aggregate_then_component_loop(self):
        top = tree()
        self.assertTrue(P.spread_aggregate(top, Always()))
        self.assertEqual(' '.join(top[1][2][1]), 'l . x = l . x * inverseX * unknown4 ;')
        self.assertEqual(' '.join(top[1][3][1]), 'l . y = l . y * inverseX * unknown4 ;')
        self.assertTrue(P.component_loop(top, Always()))
        self.assertEqual(' '.join(P.render(top[1][2])),
                         'for ( int i = 0 ; i < 2 ; ++ i ) ( & l . x ) [ i ] = ( & l . x ) [ i ] * inverseX * unknown4 ;')

    def test_swap_branches_negates_once(self):
        top = tree()
        self.assertTrue(P.swap_branches(top, Always()))
        self.assertEqual(top[1][3][1][:2], ['!', '('])
        self.assertTrue(P.swap_branches(top, Always()))
        self.assertEqual(P.render(top), P.tokens_of(BODY))

    def test_operands_swap_respects_precedence(self):
        top = tree('{ x = a + b * c; }')
        self.assertTrue(P.swap_operands(top, Always()))
        self.assertEqual(' '.join(top[1][0][1]), 'x = a + c * b ;')

    def test_compound_assignment_opens(self):
        top = tree('{ total += n * 2; }')
        self.assertTrue(P.compound_assign(top, Always()))
        self.assertEqual(' '.join(top[1][0][1]), 'total = total + ( n * 2 ) ;')

    def test_random_rewrites_keep_brackets_balanced(self):
        rng = random.Random(7)
        for _ in range(300):
            tokens = P.render(P.mutate(tree(), rng)[0])
            for a, b in ('()', '[]', '{}'):
                self.assertEqual(tokens.count(a), tokens.count(b))


class Locating(unittest.TestCase):
    SOURCE = ('// match: 1230 ?Run@Job@@\n// match: 4560 ?Stop@Job@@\n#include "x.h"\n'
              'void Job::Stop(int a) { if (a) { b(); } }\nvoid Job::Run() { c(); }\n')

    def test_definition_found_by_symbol(self):
        symbol, a, b = P.locate(self.SOURCE, 0x1230)
        self.assertEqual((symbol, self.SOURCE[a:b]), ('?Run@Job@@', '{ c(); }'))
        self.assertEqual(self.SOURCE[slice(*P.locate(self.SOURCE, 0x4560)[1:])], '{ if (a) { b(); } }')

    def test_definition_right_below_the_claim(self):
        src = '// match: 10 ?f@@\n// a note\nint f(int x)\n{\n    return x;\n}\n'
        self.assertEqual(src[slice(*P.locate(src, 0x10)[1:])], '{\n    return x;\n}')


if __name__ == '__main__':
    unittest.main()
