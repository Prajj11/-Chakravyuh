# Chakravyuh: Reddit data-access request

Submitted: 20 October 2026 through Reddit's official Data Access Request form (developer/external-app category). Reddit displayed: “Your request was successfully submitted.” Approval is pending; no ticket number was shown. The document below preserves the preparation notes; the actual submission used the form's purpose, technical description, Devvit explanation, repository and subreddit fields.

## Applicant details to complete

- Applicant full name: not requested by the submitted developer form
- Contact email: supplied privately in the submitted form
- Reddit username: supplied in the submitted form
- Team: CH26-C6GW
- Institution/organisation and applicant role: [confirm; no academic affiliation assumed]
- Source repository: https://github.com/Prajj11/codebuster (current Git origin; reviewer accessibility not independently verified)
- Intended subreddits: r/cybersecurity (proposed initial pilot)
- Requested evaluation dates: [provide start and end dates]
- Commercialisation, funding or sponsorship: [confirm]

## Suggested subject

Access eligibility and limited read-only data request — Chakravyuh coordinated-disinformation investigation prototype

## Description for the request form

We are team CH26-C6GW, developing Chakravyuh for the problem statement “Social Media Coordinated Disinformation Detection System.” We request guidance on the appropriate access programme and permission for a limited, read-only evaluation using public Reddit submissions in specifically approved subreddits.

The project studies repeated narratives, posting synchronisation and observed account interactions. Its local dashboard presents narrative timelines, account-network indicators, coverage limitations and evidence references for human review. Coordination indicators are treated as leads requiring investigation; the software does not establish that a statement is false or that a person is malicious.

The broader problem statement envisages use by law-enforcement agencies, government organisations and social-media monitoring teams. We disclose that intended application context for your assessment. The current implementation is a local prototype; this request does not assert an existing agency partnership, operational deployment or institutional research approval.

The proposed initial Reddit adapter reads newest public submissions from an explicitly configured subreddit. It uses the OAuth API and does not post, comment, vote, send messages, moderate communities or access private messages. Requested fields are public submission identifiers, titles, self-text, publication timestamps, permalinks and author usernames returned with those submissions. Deleted or unavailable authors are skipped. Comment-tree collection and historical account-profile harvesting are outside this initial request.

As a proposed initial ceiling, we request one approved subreddit, one page of up to 100 newest submissions every five minutes, for at most seven days. This is a request for approval, not a statement of entitlement or guaranteed complete collection. We will use lower limits or a different access mechanism if required. The API code supports bounded pagination, deduplication and backoff, including server-supplied Retry-After delays.

The workbench currently uses local SQLite storage, retained raw response bytes, SHA-256 evidence references and a local session token. Its export tools can produce investigation reports, so any approved Reddit evaluation would require export restrictions and an agreed retention policy. Its present immutable evidence design does not implement Reddit deletion/removal synchronisation. We therefore request your requirements for retention, removals, permitted derived analyses and report distribution, and identify that workflow as work to complete before Reddit data collection is enabled.

We are requesting access for evaluation of the described application. We are not requesting permission to train or fine-tune models on Reddit content, resell Reddit data, infer sensitive personal characteristics or identify Reddit users through off-platform matching. Any future request for model training, expanded processing, commercialisation or wider distribution would need to be separately described and approved.

Please advise whether this competition prototype is eligible for the Data API developer route, Reddit for Researchers, another agreement, or no available programme. We do not assume academic-research eligibility. If the proposed evaluation counts as research, please identify the appropriate research programme and eligibility requirements. If our proposed investigation use is unsuitable, please tell us the permitted scope rather than granting access on an inaccurate description.

## Why an external workbench is proposed

The application is an existing local Python/FastAPI and Next.js investigation workbench combining multiple independently authorised data sources. The proposed Reddit component is a read-only connector to that workbench, rather than a community-installed interactive app. We request Reddit's assessment of whether Devvit or another supported interface can satisfy this particular use; no exception to platform requirements is assumed.

## Implementation status and conditions to resolve

- Implemented: basic OAuth-token connector for newest public submissions, bounded polling, API-error backoff and first-seen deduplication.
- Not established: Reddit access approval, credentialed live verification, applicant identity/eligibility, final subreddit scope or an agreed data budget.
- Pending engineering: removal/deletion synchronisation, bounded Reddit retention and enforcement of Reddit-specific export restrictions.
- Existing analytical accuracy results do not establish performance on Reddit campaigns.

## Official submission and policy references

- [Reddit API access-request form](https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164)
- [Developer Platform and Accessing Reddit Data](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)

Reddit's current guidance requires prior approval and an accurate description of the use case. It directs academic research to its researcher programme and places restrictions on model training and user privacy. The final application must reflect the applicant's actual role and plans. No eligibility, approval, terms acceptance or submission is represented by this draft.
