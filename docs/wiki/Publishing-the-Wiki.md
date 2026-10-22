# Publishing GitHub's separate Wiki

The Markdown pages in this directory are the versioned source of truth. GitHub's Wiki is a separate git repository; committing these files to `main` does not publish that Wiki.

When the Wiki is enabled and initialized, publish from an authenticated local checkout:

```bash
git clone https://github.com/cmcintosh/FieldGuide.wiki.git
```

Copy the Markdown files from `docs/wiki` into that checkout. For the separate Wiki only, change page-to-page links such as `(Offline-Maps.md)` to `(Offline-Maps)`; GitHub Wiki uses extensionless page URLs. Keep repository links unchanged. Review the diff, commit and push using your normal GitHub authentication.

If the Wiki has not been initialized, a repository administrator must enable it and create its first page through GitHub. The GitHub connector used for the initial repository work does not expose Wiki creation/publishing; the available browser session was signed out and the wiki URL redirected to the repository. The versioned documentation is fully usable without the separate Wiki.
