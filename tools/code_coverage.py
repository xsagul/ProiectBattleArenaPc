"""Disjoint byte ranges for source-reconstruction accounting. Bounds are half-open."""
import bisect


def merge(ranges):
    result = []
    for first, last in sorted(ranges):
        if last <= first:
            continue
        if result and first <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], last))
        else:
            result.append((first, last))
    return result


def intersect(a, b):
    a, b = merge(a), merge(b)
    result, left, right = [], 0, 0
    while left < len(a) and right < len(b):
        first, last = max(a[left][0], b[right][0]), min(a[left][1], b[right][1])
        if first < last:
            result.append((first, last))
        if a[left][1] <= b[right][1]:
            left += 1
        else:
            right += 1
    return result


def subtract(ranges, covered):
    ranges, covered = merge(ranges), merge(covered)
    result, index = [], 0
    for first, last in ranges:
        while index < len(covered) and covered[index][1] <= first:
            index += 1
        current, j = first, index
        while j < len(covered) and covered[j][0] < last:
            a, b = covered[j]
            if a > current:
                result.append((current, min(a, last)))
            current = max(current, b)
            if current >= last:
                break
            j += 1
        if current < last:
            result.append((current, last))
    return result


def length(ranges):
    return sum(last - first for first, last in merge(ranges))


def inventory(index_ranges, verified, text_bounds):
    """Keep proven instruction bytes which the index's padding heuristic accidentally removed.

    Only fully verified compiled functions augment the inventory, and only within the known text region.
    Candidate lengths and uncertain library shapes must not expand it.
    """
    spans = intersect(((rva, rva + size) for rva, size in verified.items()), [text_bounds])
    return merge(list(index_ranges) + spans)


def partition(index_ranges, rows):
    """Attribute only byte ranges, keeping any unmatched tail of a partially reconstructed index entry.

    rows: dictionaries of function address -> compiled length, in reporting precedence. Returns newly owned
    ranges per row and the remaining ranges. Function labels themselves do not prove byte coverage.
    """
    code = merge(index_ranges)
    owned, parts = [], []
    for row in rows:
        spans = intersect(((rva, rva + size) for rva, size in row.items()), code)
        part = subtract(spans, owned)
        parts.append(part)
        owned = merge(owned + part)
    return parts, subtract(code, owned)


def entries_with_uncovered_bytes(index_ranges, remaining):
    remaining = merge(remaining)
    ends = [end for start, end in remaining]
    count = 0
    for first, last in index_ranges:
        if last <= first:
            continue
        k = bisect.bisect_right(ends, first)
        if k < len(remaining) and remaining[k][0] < last:
            count += 1
    return count
