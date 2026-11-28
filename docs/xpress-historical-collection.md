# Staging historical XpressJobs advertisements

Archived copies of the [XpressJobs sitemap](https://xpress.jobs/sitemap.xml) can list expired detail URLs. Some captures contain only organization and listing URLs. Read the XML and keep successful sitemap captures, their timestamps, and the vacancy links that produced the candidate IDs. The [Sri Lanka Software Jobs tracker](https://github.com/Senadeera-NK/sri-lanka-software-jobs) also recorded some XpressJobs vacancies.

Resolve discovered public vacancy IDs using the publisher's detail response at `https://xpress.jobs/api/jobs/publishedJob?jobId=<id>`. Collect sequentially, using at least the 2.5-second delay in the source registry. Stop on access restrictions or rate limits. Save each JSON body under its numeric vacancy ID and record a JSONL manifest with the following fields.

| Field | Value |
| --- | --- |
| `id` | Vacancy ID as a string |
| `status` | HTTP status |
| `file` | Filename such as `188419.json` for a successful response |
| `publisher_url` | Exact detail response URL |
| `sha256` | SHA-256 of the saved response |
| `discovery` | Sitemap replay, tracker commit, or original public advert used for discovery |

```bash
python -m tools.stage_xpress_history xpress-stage.csv captures/attempts.jsonl --as-of 2026-11-28
```

Staging uses the publisher's `createdDate` and checks that the original date is consistent with the discovery snapshot, where available. Sitemap modification dates guide sampling. The tool screens for Sri Lankan job locations, technical roles, and usable descriptions. It redacts direct email addresses and phone numbers and records exclusions. Image-only adverts require a separate OCR review.

Reconcile source IDs with the master and earlier batches before import. Run the normal cleaning and role-review workflow. Retain zero-skill jobs for valid denominators and report each source's posting-month counts, including gaps. The available archived sitemaps and surviving detail responses sample different periods unevenly.
