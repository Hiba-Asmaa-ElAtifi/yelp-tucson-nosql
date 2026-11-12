# Contributing

## Branch workflow

1. Update the local `main` branch.
2. Create a focused branch named `feature/<short-task>`.
3. Keep commits small and descriptive.
4. Open a pull request into `main`.
5. Ask at least one teammate to review changes before merging.

## Data safety

Do not commit raw or transformed Yelp data, MongoDB volumes, credentials, or `.env` files. Before every push, verify the staged files with:

```bash
git status --short
git diff --cached --stat
```

## Verification

Every pull request should explain:

- what changed;
- how it was tested;
- which dataset scope was used;
- whether counts or schemas changed;
- any remaining limitation.

