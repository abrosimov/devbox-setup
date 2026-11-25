# Evidence rules

How strong a sentence may be, given what it rests on. Apply them to every sentence written or
changed, in stage 5 to the whole document, and to every reviewer's proposed wording.

## Contents

- [Strength](#strength)
- [The deck as a source](#the-deck-as-a-source)
- [Public sources and dates](#public-sources-and-dates)
- [Observations and causes](#observations-and-causes)
- [Numbers, counts and formulas](#numbers-counts-and-formulas)
- [Quotes, inventories and law](#quotes-inventories-and-law)
- [Draft and acceptable forms](#draft-and-acceptable-forms)
- [Words to distrust: manual checklist](#words-to-distrust-manual-checklist)

## Strength

- No statement stronger than its source. "The deck says X" is safe; "X is the case" is not.
- Keep every qualifier the source carries: tentative, expected, planned, in the regions listed,
  if in use, by default.
- "May" is not "is"; "not stated" is not "absent"; "no longer promised" is not "no longer
  happens".
- An inference ("so", "therefore") stands only if it strictly follows. Where it does not, say what
  cannot be told.
- "Not known" is true only after looking: read the public source first.
- A fact the client gave in conversation is a source and is attributed as one; it does not become
  a fact about the system.
- An assumption a calculation uses is stated at its start.

## The deck as a source

- A claim about a slide counts only if the slide's image was seen, not only its text layer.
- "The deck does not say" needs a search of every slide, text and images, for a counter-example.
- A screenshot or diagram describes what a slide shows, not what is set up.
- Events after the deck's last-saved date are not evidence of the authors' neglect. Say when the
  event happened relative to the save.
- Where parts of the deck disagree, write a bounded "what follows / what does not": what both
  parts support, and what neither settles.

## Public sources and dates

- Search first, then open the page. Record the read date next to the link; a publication date does
  not replace it.
- Use a date only from a page actually opened. If the primary page will not open, do not use
  third-party figures in its place; record the attempt and its date.
- If the maker's own pages disagree on a date, drop the date and say the pages disagree.
- Absolute dates beat relative ones ("3 days ago").
- **Stale cache**: the same relative timestamp on reads days apart means a cached copy. Mark the
  reading unverified and name the regional storefront or mirror that served it.
- Read a second storefront or address before writing "not updated". The later date wins.
- Re-read deadline facts (end of support, retirement, announced regions) on every edit day.

## Observations and causes

- State an observation with its known context and its effect on the user; neither assert nor
  guess a cause.
- Where a cause matters to what is checked first, offer rival explanations, each with the
  observation that would tell them apart.

## Numbers, counts and formulas

- Say whether a figure was rounded. "Over N" is a floor, not an estimate.
- Name the comparison base for every percentage and every "small" or "large".
- Formula variables match the data requested in the data-request appendix, name for name.
- Distinguish the kind of figure: quoted or list price versus billed, estimate versus measured,
  average versus peak.
- Counters in the text ("three of the components") are recounted in stage 7.

## Quotes, inventories and law

- Quotes are verbatim. A quote assembled from several places is flagged as composite.
- Inventory words (every, only, one, both, all) need a search that proves the inventory.
- An unconditional legal conclusion becomes a question for counsel: state what the law permits
  and under which conditions, and leave whether they are met to counsel.
- "No such product exists" becomes "no product of that name was found at [vendor]".

## Draft and acceptable forms

| Draft | Acceptable | Rule |
|---|---|---|
| "The server no longer receives security fixes." | "The maker's promise of security fixes ended on [date]." | releases continued after the date; keep the source's strength |
| "The system stores data outside the country." | "The deck places the platform on [cloud provider], which has no region open in [country] as of [read date]." | nobody has seen the system |
| "Nothing would notice a payment failure." | "The deck names no monitoring of the payment provider." | the deck names other monitoring; "nothing" overreaches |
| "The app was logged out, probably by a single-session policy." | "The app was logged out when it updated; the user has to log in again." | no guessed cause |
| "The model retires on [date]." | "The maker gives [date] as the tentative retirement date." | qualifier kept |
| "Two reports can show different totals." | "It cannot be told whether its reports agree." | the inference did not follow |
| "The apps' status is not known." | (read the public store page first) | "not known" only after looking |
| "[Component] retirement shows upkeep is behind." | "[Maker] scheduled it for retirement on [date], after the deck was saved." | event after the source was saved |
| "[Cloud provider] lists no region in [country]." | "[Cloud provider] has no region open there; one is announced for [month]." | announced is not open; both are said |
| "The deck names one log store: [log tool]." | "[Log tool] for application logs; the picture on slide [N] also shows audit records kept in [database]." | a count needs a search of all slides, images included |
| "The service operates in [city] only." (from client chat) | "The deck does not say where it operates; Appendix [X] assumes [city]." | chat facts are attributed; assumptions stated |
| "Slide [N] shows $[X] paid for licences." | "Slide [N] gives list prices; only the [vendor] line is marked as billed." | a quoted price is not money paid |
| "The only places it could sit are [A] and [B]." | "Places it could sit include [A], [B], [C]." | inventory word without a proven inventory |
| "The weekly batch adds [x]% to processing, which is small." | "Against the week's volume it looks small; the batch runs in one night, so its load needs per-hour figures." | comparison base named |
| "Two application servers share the load." | "The slide quotes what the hosting plan allows (up to two servers), not how many are set up." | a capability on a slide is not configuration |
| "Holding data abroad is allowed." | "The law permits it under conditions; whether they are met is for counsel." | legal conclusion becomes a question |
| "No such product exists." | "No [vendor] product of that name was found." | absence only as far as searched |
| "Backups: not mentioned." | "The managed database backs up by default unless switched off; retention and restore tests are not known." | read the public default before "not known" |
| "Nobody has looked at the running system." | "No server, database or account has been inspected." | say exactly what was not done |

## Words to distrust: manual checklist

Search the draft for each and confirm the source carries the full strength. There is no script
for this yet; run it by hand and record the result in `checks.md`.

- [ ] no, none, nothing, never
- [ ] all, every, both, each, only, one, the only
- [ ] cannot, impossible, always
- [ ] so, therefore, thus, which means, shows that
- [ ] is, does, runs, stores (where the source says names, lists, describes)
- [ ] dropped qualifiers: tentative, expected, planned, announced, by default, if in use, in the
      regions listed
- [ ] "not known", "not mentioned", "absent" (was the public source read first?)
- [ ] "not updated", "outdated" (were two storefronts or addresses read?)
- [ ] "over", "about", "around" (floor, rounding, or estimate: which?)
- [ ] relative dates ("3 days ago", "last week") left in place of absolute ones
- [ ] judgements of size ("far too low", "huge"); describe what the source does instead
- [ ] causes ("because", "due to", "probably") attached to an observation
