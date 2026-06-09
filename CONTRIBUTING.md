# Contributing

Thanks for helping improve `ctf-codex-toolkit`.

## Development Checks

Run these before opening a pull request:

```powershell
npm run smoke
npm pack --dry-run
```

The GitHub Actions workflow runs the same checks on pushes and pull requests.

## Release Notes

The package is designed to be installed by users from npm or GitHub without copying provider configuration or secrets.

Before publishing a release:

```powershell
npm run smoke
npm pack --dry-run
npm publish --access public
```

If the unscoped package name is unavailable on npm, publish a scoped package and update the install examples in `README.md`.

## Third-Party Content

Keep `THIRD_PARTY_NOTICES.md` up to date when bundled skills, tools, snippets, or browser automation dependencies are added or changed.

