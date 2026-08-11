Drop FOIA/public-records response PDFs here, then run:

```sh
npm run foia
```

Optionally add a same-named `.json` sidecar for compliance-deadline
checking, e.g. `some-response.pdf` + `some-response.json`:

```json
{
	"agency": "Some Police Department",
	"state": "IL",
	"requestDate": "2024-03-15",
	"responseDate": "2024-05-21",
	"requestSubject": "Flock Safety financial materials"
}
```

Files here aren't committed to the repo (see `.gitignore`) — they're
often third-party documents (redacted government responses, sometimes
large) that aren't ours to redistribute in source control.
