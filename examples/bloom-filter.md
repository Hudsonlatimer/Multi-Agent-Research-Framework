# How a Bloom filter rejects a missing key

> 1 source cited · 3 claims · 3 quotes · 0 unknown citations

A Bloom filter tests set membership. It can say a key is definitely absent. False positives are possible, but false negatives are not. [S1]

## Membership

- A Bloom filter tests whether an element is a member of a set. [S1]
  > A Bloom filter is a space-efficient probabilistic data structure, conceived by Burton Howard Bloom in 1970, that is used to test whether an element is a member of a set.

## False results

- False positive matches are possible, but false negatives are not. [S1]
  > False positive matches are possible, but false negatives are not.
- Burton Howard Bloom conceived the structure in 1970. [S1]
  > A Bloom filter is a space-efficient probabilistic data structure, conceived by Burton Howard Bloom in 1970, that is used to test whether an element is a member of a set.

## Limitations

The source does not give the false-positive rate formula or the bit-array layout.

## Bibliography

- [S1] Bloom filter. https://en.wikipedia.org/wiki/Bloom_filter (retrieved 2026-10-16T16:49:21+00:00)
