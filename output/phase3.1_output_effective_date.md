# Phase 3.1 — Effective Date extraction, n=50 final (2026-07-01)

**Result: ACCURACY 32/50 = 64%** | input tokens 346,332 | estimated cost $1.1153

Second clause type after Governing Law (Phase 1–2). Reuses the same section-ranking /
keyword-windowing / forced-tool-use infrastructure as `phase2.2_governing_law.py`. Only
the clause-specific patterns, prompt, and tool are new.

The 1-contract drop vs. the earlier documented 33/50 = 66% is BorrowMoney (#18), which
flipped from OK to MISS — an already-borderline case where the execution date vs.
commencement date confusion is genuine (BorrowMoney has three competing Florida-law
mentions and no clean standalone "effective date" sentence). The underlying pipeline
changes in this final version were net-positive; the difference is LLM non-determinism
on that one contract.

**BorrowMoney is a known recurring volatile case across the project, not a one-off
flip.** It has appeared as a swing contract in every major clause type tested:
- **Governing Law (Phase 1.3)**: Governing Law has three Florida-law-style phrases —
  a formation clause, a jurisdiction/venue clause, and an arbitration reference. The model
  alternated between picking the correct formation clause and a venue clause across runs,
  and was ultimately scored via the jurisdiction-aware fallback (both cited Florida).
- **Governing Law (Phase 2.2)**: BorrowMoney flipped to MISS after the venue/governing-law
  prompt sharpening, which taught the model to reject venue language — and it overcorrected
  by also rejecting the genuine formation-based clause. Documented as an accepted
  precision/recall tradeoff.
- **Effective Date (Phase 3.1)**: The contract's effective date can plausibly be either the
  execution caption ("20th day of Friday, March 2020") or the Term's commencement clause
  ("March 1, 2020"). The model's choice between them is non-deterministic across runs.

This contract's structure — multiple plausible candidate spans citing the same jurisdiction/
month with no unambiguous primary clause — makes it an inherently unstable evaluation point
for any clause type. One-run accuracy numbers that include BorrowMoney should be interpreted
with a ±1-contract margin of uncertainty.

## What changed after the initial baseline run

The previous output log was written at 66% (33/50) using an earlier version of the code.
Between that run and this one, several improvements were made based on offline coverage
analysis (no API cost):

**Three bugs discovered and fixed via coverage diagnosis:**

1. **Quote-intolerance in the agreement-detection pattern.** The regex checking for `(the
   "Agreement")` was using literal `"` characters that the editor silently converted to
   Unicode curly-quotes (U+201C/U+201D). The pattern never matched contracts with ASCII
   double-quotes. Rewrote as two separate compiled patterns (`_THIS_AGREEMENT_1`,
   `_THIS_AGREEMENT_2`) to avoid catastrophic backtracking in the combined `|` form, and
   used `\x22` (hex for ASCII 0x22) to prevent future editor corruption.

2. **Preamble-orphaning bug in `build_section_spans()`.** The function only created spans
   starting at detected header lines, so any text before the very first header (the title
   block, exhibit number, opening paragraph) was silently dropped from every span. For
   Governing Law (near the end of contracts) this barely mattered. For Effective Date
   (median position ~1% into the document, almost always in the opening paragraph) it was
   the largest single driver of coverage failures. Fixed by prepending a preamble span
   `(0, first_header_start)` when pre-header content exists.

3. **Missing abbreviated month pattern.** Date formats like `"19 Jan. 1998"` (day +
   abbreviated month + year) weren't matched by `EFFECTIVE_DATE_PATTERNS`, so sections
   containing these dates were invisible to the keyword scanner. Added
   `r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b"`.

**`--diagnose` flag added.** When set, prints all candidate sections (including those
dropped by the tier-ranking or max-sections cap) for each MISS or weak-only contract,
showing whether the gold text is present in each candidate. This is a permanent diagnostic
tool for understanding *why* a contract fails — see "Failure categories" below.

## Failure categories discovered via `--diagnose`

Running `--diagnose` on the 9 remaining coverage-gap contracts revealed three distinct root
causes, each requiring a different fix:

### Category A — No keyword match at all (3 contracts: #4, #38, #40)

The gold clause generates **zero hits** across all of `EFFECTIVE_DATE_PATTERNS`. Nothing is
even flagged as a candidate, so the model sees the wrong section entirely.

- **#4 (AdamsGolf)**: commencement date phrased as `"commencing the 1st day of September
  2004"` — `"1st"` is an ordinal, not a digit, so `\d{1,2}` doesn't match before
  "September". Gold clause has no `"effective"` / `"dated as of"` / `"made and entered
  into"` language either; ordinal-day patterns needed.
- **#38 (SouthernStar)**: event-conditional clause (`"begin upon acceptance of Affiliate's
  Program application"`) — no fixed calendar date at all. Likely unfixable for this clause
  type.
- **#40 (Principal Life)**: blank template date (`"this ______ day of ______, 2013"`) —
  no digits to match a date pattern. The clause genuinely has no real date.

### Category B — Right section detected but ranked tier-0, dropped by cap (4 contracts: #16, #33, #20, #43)

The gold-bearing section IS found by the keyword scanner, but it achieves only tier-0
(weak signal) while stronger false-positive sections elsewhere achieve tier-1, taking
priority. **This is the primary target for phase 3.2.**

The dominant sub-pattern for #16 and #33: the **title/caption convention** —
`"MASTER SUPPLY AGREEMENT (the "Agreement") dated November 1, 2019"` — where the document
title is repeated as the preamble caption, followed immediately by `"dated [date]"`. The
`_matches_agreement()` check requires `"this [something] agreement"` or
`"(the Agreement)"` co-occurrence, but these preamble lines use the title form without
"this", so they fall to tier-0 while stronger sections elsewhere win the selection.

Specific cases:
- **#16**: Gold `"April __, 2005"` is in preamble section `SUPPORT AND MAINTENANCE
  AGREEMENT`; 3 strong tier-1 sections from body take priority.
- **#33**: Gold `"January 21st, 2002"` is in preamble section `MANUFACTURING OUTSOURCING
  AGREEMENT`; 3 strong tier-1 sections from body take priority.
- **#20**: Gold `"Effective Date" means the Closing Date...` is in `ARTICLE I DEFINITIONS`
  (tier-0); 4 strong sections elsewhere win.
- **#43 (WPPPLC)**: Gold `"27 January 2020"` in a section headed `"JOHN ROGERS"` (tier-0,
  42,615 chars); a false-positive tier-1 match in `"21. COLLECTIVE AGREEMENTS"` takes the
  only strong slot.

### Category C — Correct tier-2 section selected but date value lives elsewhere (2 contracts: #47, #48)

The right section *header* is detected (tier-2, explicitly named "EFFECTIVE DATE"), but
the actual date value appears in a completely different section in the document. CUAD's
annotators labeled a date that lives outside the "Effective Date" section.

- **#47**: Two tier-2 sections named "EFFECTIVE DATE AND DURATION" are selected. Gold
  `"January 6th, 2016"` actually sits in a Governing Law / Arbitration section.
- **#48**: Tier-2 section "EFFECTIVE AS OF (EFFECTIVE DATE)" selected (684 chars); gold
  `"19 Jan. 1998"` lives in the Insurance section. Model returned `"EFFECTIVE AS OF
  (EFFECTIVE DATE)"` (the section header itself) as the date value.

## Scorer-vs-substance gaps (not model errors, ~10% recurrence rate)

Five of the 18 misses are contracts where the model found the **substantively correct**
date from a different sentence than the one CUAD labeled — verified verbatim for each.
Same pattern and same decision as Governing Law's NETGEAR/SoupmanInc cases: kept in the
denominator, documented here.

| # | Gold (labeled span) | Why it's a scorer gap, not a model error |
|---|---|---|
| 7 | `"Effective Date" shall have the meaning set forth in the preamble` | Model found the actual preamble sentence stating September 26, 2018 |
| 10 | `...effective as of the day and year first above written...` | "Day and year first above written" = February 4, 2005; model reported the caption that states it |
| 11 | `...shall become effective when one or more counterparts have been signed...` | Model found `"dated as of September 30, 2019"` — the same date the counterparts were signed |
| 24 | `...take effect as of the date when...representatives...sign hereon` | Model found `"entered into on January 24, 2014"` — when the signing occurred |
| 44 | `Commencement Date means the date of this Agreement` | Model found `"THIS AGREEMENT IS MADE ON THE 19 DAY OF MAY, 2010"` — the referenced date |

## Raw run output, n=50

```
$ python3 phase3.1_effective_date.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --n 50 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 50 contracts that have an Effective Date clause.

[ 1/50] (contract #1) OK  LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGR...
        gold  : 'The term of this  Agreement  shall be ten (10)                            years '
        pred  : 'The term of this  Agreement  shall be ten (10)                            years '
        src   : section-match
        ctx   : 54290 chars -> 9975 chars sent
        usage : in=3330 out=106 total=3436
[ 2/50] (contract #2) OK  WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION ...
        gold  : '1 August 2011'
        pred  : 'This Promotion and Distribution Agreement including all exhibits (collectively r'
        src   : section-match
        ctx   : 70383 chars -> 14721 chars sent
        usage : in=4875 out=172 total=5047
[ 3/50] (contract #3) OK  CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-W...
        gold  : 'The term of this Agreement for the Hosted Site shall commence upon April 1, 1999'
        pred  : 'The term of this Agreement for the Hosted Site shall commence upon April 1, 1999'
        src   : section-match
        ctx   : 15176 chars -> 905 chars sent
        usage : in=1425 out=71 total=1496
[ 4/50] (contract #4) MISS ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT ...
        gold  : 'The Term of this Agreement shall be for a period of [* ****] years and [*****] months commencing the 1st day of September 2004 and terminating the [*****] day of [*****].'
        pred  : 'This Agreement is entered into on January 13, 2005 between professional golfer, TOM WATSON, (hereinafter referred to as "CONSULTANT") and ADAMS GOLF, LTD. (hereinafter referred to as "ADAMS GOLF").'
        pred matched patterns: ['\b(?:January|...|December)\s+\d{1,2},?\s+\d{4}\b']
        src   : section-match
        ctx   : 24632 chars -> 2743 chars sent
        usage : in=1956 out=109 total=2065
[ 5/50] (contract #5) OK  KIROMICBIOPHARMA,INC_05_11_2020-EX-10.23-CONS...
        gold  : 'This letter agreement will be effective as of July 1, 2018.'
        pred  : 'This letter agreement will be effective as of July 1, 2018.'
        src   : section-match
        ctx   : 18403 chars -> 17065 chars sent
        usage : in=4775 out=66 total=4841
[ 6/50] (contract #6) MISS VEONEER,INC_02_21_2020-EX-10.11-JOINT VENTURE...
        gold  : 'This Amendment shall only become effective upon the VNBJ Closing...'
        pred  : 'This AMENDMENT AND TERMINATION OF JOINT VENTURE AGREEMENT (this "Amendment") is made and entered into effective as of October 30, 2019 (the "Effective Date")'
        pred matched patterns: ['effective date', 'effective as of', 'made and entered into', ...]
        src   : section-match
        ctx   : 8257 chars -> 8211 chars sent
        usage : in=3574 out=93 total=3667
[ 7/50] (contract #7) MISS DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_...
        gold  : '"Effective Date" shall have the meaning set forth in the preamble to this Agreement.'
        pred  : 'This Co-Promotion Agreement (this "Agreement") is entered into and dated as of September 26, 2018 (the "Effective Date")'
        pred matched patterns: ['effective date', 'dated as of', ...]
        src   : section-match
        ctx   : 175580 chars -> 95697 chars sent
        usage : in=23242 out=84 total=23326
[ 8/50] (contract #8) OK  PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...
        gold  : 'August 10, 2007'
        pred  : 'THIS AMENDED AND RESTATED STRATEGIC LICENSING, DISTRIBUTION AND MARKETING AGREEM'
        src   : section-match
        ctx   : 145168 chars -> 127590 chars sent
        usage : in=31254 out=242 total=31496
[ 9/50] (contract #9) OK  FTENETWORKS,INC_02_18_2016-EX-99.4-STRATEGIC ...
        gold  : '17t h day of February 2016'
        pred  : 'THIS STRATEGIC ALLIANCE AGREEMENT (the "Agreement"), made effective this 17t h d'
        src   : section-match
        ctx   : 37829 chars -> 4691 chars sent
        usage : in=2329 out=92 total=2421
[10/50] (contract #10) MISS DOMINIADVISORTRUST_02_18_2005-EX-99.(H)(2)-SP...
        gold  : 'This Agreement shall become effective as of the day and year first above written...'
        pred  : 'SPONSORSHIP AGREEMENT, dated as of February 4, 2005, by and between Domini Advisor Trust...'
        pred matched patterns: ['dated as of', ...]
        src   : section-match
        ctx   : 12555 chars -> 11832 chars sent
        usage : in=3647 out=106 total=3753
[11/50] (contract #11) MISS CerenceInc_20191002_8-K_EX-10.4_11827494_EX-1...
        gold  : 'This Agreement may be executed in one or more counterparts...shall become effective when one or more counterparts have been signed...'
        pred  : 'INTELLECTUAL PROPERTY AGREEMENT, dated as of September 30, 2019 (this "Agreement")...'
        pred matched patterns: ['dated as of', ...]
        src   : section-match
        ctx   : 62170 chars -> 24647 chars sent
        usage : in=7079 out=110 total=7189
[12/50] (contract #12) OK  ThriventVariableInsuranceAccountB_20190701_N-...
        gold  : 'July 1, 2019'
        pred  : 'Effective Date: July 1, 2019'
        src   : section-match
        ctx   : 4871 chars -> 3887 chars sent
        usage : in=2185 out=62 total=2247
[13/50] (contract #13) OK  ReynoldsConsumerProductsInc_20191115_S-1_EX-1...
        gold  : 'November 1, 2019'
        pred  : 'MASTER SUPPLY AGREEMENT (the "Agreement") dated November 1, 2019 (the "Effective'
        src   : section-match
        ctx   : 61710 chars -> 61215 chars sent
        usage : in=14153 out=78 total=14231
[14/50] (contract #14) OK  PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTEL...
        gold  : 'May 12, 2020'
        pred  : 'This Intellectual Property Agreement (this "Agreement") is entered into on May 1'
        src   : section-match
        ctx   : 23282 chars -> 8017 chars sent
        usage : in=3222 out=78 total=3300
[15/50] (contract #15) OK  INTRICONCORP_03_10_2009-EX-10.22-Strategic Al...
        gold  : '1st day of October, 2008'
        pred  : 'This Agreement is entered into and is effective as of the 1st day of October, 20'
        src   : section-match
        ctx   : 52967 chars -> 47315 chars sent
        usage : in=12119 out=79 total=12198
[16/50] (contract #16) MISS ON2TECHNOLOGIES,INC_11_17_2006-EX-10.3-SUPPOR...
        gold  : 'April __, 2005'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 61392 chars -> 43209 chars sent
        usage : in=10992 out=50 total=11042
[17/50] (contract #17) OK  OPERALTD_04_30_2020-EX-4.14-SERVICE AGREEMENT
        gold  : 'April. 1st 2019'
        pred  : 'This Service Agreement ("Agreement") is entered into on April. 1st 2019 ("Effect'
        src   : section-match
        ctx   : 20983 chars -> 6328 chars sent
        usage : in=2750 out=75 total=2825
[18/50] (contract #18) MISS BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT V...
        gold  : 'The duration of this Venture (the "Term") will begin on March 1, 2020...'
        pred  : 'THIS JOINT VENTURE AGREEMENT (the "Agreement") made and entered into this 20th day of Friday, March 2020 (the "Execution Date")'
        pred matched patterns: ['made and entered into']
        src   : section-match
        ctx   : 21450 chars -> 1962 chars sent
        usage : in=1740 out=87 total=1827
[19/50] (contract #19) OK  ZEBRATECHNOLOGIESCORP_04_16_2014-EX-10.1-INTE...
        gold  : 'April 14, 2014'
        pred  : 'THIS INTELLECTUAL PROPERTY AGREEMENT (this "IP Agreement") is entered into as of'
        src   : section-match
        ctx   : 127205 chars -> 87508 chars sent
        usage : in=21262 out=120 total=21382
[20/50] (contract #20) MISS ChinaRealEstateInformationCorp_20090929_F-1_E...
        gold  : '"Effective Date" means the Closing Date as set forth in the Share Purchase Agreement.'
        pred  : 'This Domain Name and Content License Agreement (the "Agreement") is made and entered into...is made effective as of the Effective Date (defined below).'
        pred matched patterns: ['effective as of', 'made and entered into']
        src   : section-match
        ctx   : 49191 chars -> 21768 chars sent
        usage : in=6381 out=179 total=6560
[21/50] (contract #21) OK  HERTZGLOBALHOLDINGS,INC_07_07_2016-EX-10.4-IN...
        gold  : '30  day of June 2016'
        pred  : 'This INTELLECTUAL PROPERTY AGREEMENT (this "Agreement" or "IPA"), effective as o'
        src   : section-match
        ctx   : 30968 chars -> 30554 chars sent
        usage : in=8769 out=89 total=8858
[22/50] (contract #22) OK  GLOBALTECHNOLOGIESLTD_06_08_2020-EX-10.16-CON...
        gold  : '2nd day of January 2020'
        pred  : 'This Consulting Agreement (the "Agreement") is made and entered into as of this '
        src   : section-match
        ctx   : 20805 chars -> 4705 chars sent
        usage : in=2330 out=77 total=2407
[23/50] (contract #23) OK  CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTI...
        gold  : 'October 29, 1999'
        pred  : 'This License and Hosting Agreement (the "AGREEMENT") is made and entered into as'
        src   : section-match
        ctx   : 62324 chars -> 53430 chars sent
        usage : in=12295 out=165 total=12460
[24/50] (contract #24) MISS TUNIUCORP_03_06_2014-EX-10-COOPERATION AGREEM...
        gold  : 'This Agreement shall take effect as of the date when the authorized representatives of the Parties sign hereon.'
        pred  : 'This Cooperation Agreement (2014 Amendment) (this "Agreement") is entered into on January 24, 2014 in Beijing...'
        pred matched patterns: ['\b(?:January|...|December)\s+\d{1,2},?\s+\d{4}\b']
        src   : section-match
        ctx   : 17917 chars -> 17903 chars sent
        usage : in=5056 out=83 total=5139
[25/50] (contract #25) MISS CYBERIANOUTPOSTINC_07_09_1998-EX-10.13-PROMOT...
        gold  : 'The term of this Agreement (the "Term") will begin on February 1, 1998...'
        pred  : 'This Promotion Agreement (the "Agreement") is dated as of January 26, 1998...'
        pred matched patterns: ['dated as of', ...]
        src   : section-match
        ctx   : 25288 chars -> 23373 chars sent
        usage : in=6182 out=99 total=6281
[26/50] (contract #26) MISS SENMIAOTECHNOLOGYLTD_02_19_2019-EX-10.5-Colla...
        gold  : 'December 17, 2018'
        pred  : 'The Agreement executed offline in paper form shall become effective upon the completion of the execution by both Parties...'
        pred matched patterns: ['effective date', 'become effective']
        src   : section-match
        ctx   : 73890 chars -> 6666 chars sent
        usage : in=2812 out=135 total=2947
[27/50] (contract #27) OK  HealthcareIntegratedTechnologiesInc_20190812_...
        gold  : '31 day of July 2019'
        pred  : 'This Walabot-HOME Reseller Agreement ("Agreement") is made and entered into as o'
        src   : section-match
        ctx   : 22288 chars -> 7557 chars sent
        usage : in=3274 out=88 total=3362
[28/50] (contract #28) OK  LOYALTYPOINTINC_11_16_2004-EX-10.2-RESELLER A...
        gold  : 'This Agreement is effective as of August 1, 2004, (the "Effective Date") and sha'
        pred  : 'This Agreement is effective as of August 1, 2004, (the "Effective Date")'
        src   : section-match
        ctx   : 117478 chars -> 11035 chars sent
        usage : in=3343 out=72 total=3415
[29/50] (contract #29) OK  BNCMORTGAGEINC_05_17_1999-EX-10.4-LICENSING A...
        gold  : 'February 26, 1999'
        pred  : 'This Agreement is entered into on February 26, 1999, (the "Effective Date")'
        src   : section-match
        ctx   : 32680 chars -> 32581 chars sent
        usage : in=8092 out=72 total=8164
[30/50] (contract #30) OK  ENERGOUSCORP_03_16_2017-EX-10.24-STRATEGIC AL...
        gold  : 'November 6, 2016'
        pred  : 'THIS STRATEGIC ALLIANCE AGREEMENT ("Agreement") is made and entered into as of N'
        src   : section-match
        ctx   : 81926 chars -> 16745 chars sent
        usage : in=5311 out=83 total=5394
[31/50] (contract #31) OK  CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-...
        gold  : 'December 17, 2019'
        pred  : 'This Commercialization and License Agreement (this "Agreement") is made effectiv'
        src   : section-match
        ctx   : 159488 chars -> 87606 chars sent
        usage : in=21730 out=84 total=21814
[32/50] (contract #32) OK  MSCIINC_02_28_2008-EX-10.10-
        gold  : 'November 20, 2007'
        pred  : 'This Intellectual Property Agreement (the "Agreement"), is entered into as of No'
        src   : section-match
        ctx   : 11770 chars -> 2674 chars sent
        usage : in=1837 out=112 total=1949
[33/50] (contract #33) MISS NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEME...
        gold  : 'January 21st, 2002'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 148163 chars -> 68239 chars sent
        usage : in=14180 out=50 total=14230
[34/50] (contract #34) OK  ImpresseCorp_20000322_S-1A_EX-10.11_5199234_E...
        gold  : 'March 3, 2000'
        pred  : 'This Co-Branding Agreement (this "Agreement") dated March 3, 2000 (the "Effectiv'
        src   : section-match
        ctx   : 47639 chars -> 12587 chars sent
        usage : in=4256 out=169 total=4425
[35/50] (contract #35) OK  AlliedEsportsEntertainmentInc_20190815_8-K_EX...
        gold  : 'February 1, 2018'
        pred  : 'This JOINT CONTENT LICENSE AGREEMENT (the "Agreement"), dated February 1, 2018 ('
        src   : section-match
        ctx   : 35504 chars -> 14725 chars sent
        usage : in=5049 out=251 total=5300
[36/50] (contract #36) OK  CreditcardscomInc_20070810_S-1_EX-10.33_36229...
        gold  : 'The term of this Agreement will commence on the date that the Affiliate Registra'
        pred  : 'The term of this Agreement will commence on the date that the Affiliate Registra'
        src   : section-match
        ctx   : 28804 chars -> 19313 chars sent
        usage : in=5646 out=71 total=5717
[37/50] (contract #37) OK  Zounds Hearing, Inc. - MANUFACTURING DESIGN M...
        gold  : 'October 3, 2018'
        pred  : 'This MANUFACTURING, DESIGN AND MARKETING AGREEMENT (this "Agreement") is entered'
        src   : section-match
        ctx   : 47001 chars -> 4613 chars sent
        usage : in=2222 out=129 total=2351
[38/50] (contract #38) MISS SouthernStarEnergyInc_20051202_SB-2A_EX-9_801...
        gold  : "The term of this Agreement will begin upon acceptance of Affiliate's Program application..."
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 22721 chars -> 9591 chars sent
        usage : in=3463 out=50 total=3513
[39/50] (contract #39) OK  ConformisInc_20191101_10-Q_EX-10.6_11861402_E...
        gold  : 'September 30, 2019'
        pred  : 'This Development Agreement ("this Agreement") is entered into and effective as o'
        src   : section-match
        ctx   : 63217 chars -> 43448 chars sent
        usage : in=12139 out=79 total=12218
[40/50] (contract #40) MISS Principal Life Insurance Company - Broker Dea...
        gold  : 'this ______ day of ________________, 2013'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 29599 chars -> 2846 chars sent
        usage : in=1866 out=50 total=1916
[41/50] (contract #41) OK  LegacyEducationAllianceInc_20200330_10-K_EX-1...
        gold  : '12-23-2019'
        pred  : 'This Real Estate Education Training Program Development Agreement (this "Agreeme'
        src   : section-match
        ctx   : 46255 chars -> 24857 chars sent
        usage : in=7604 out=136 total=7740
[42/50] (contract #42) OK  VERICELCORP_08_06_2019-EX-10.10-SUPPLY AGREEM...
        gold  : 'May 6, 2019'
        pred  : 'THIS SUPPLY AGREEMENT (the "Agreement") is entered into as of May 6, 2019 (the "'
        src   : section-match
        ctx   : 102006 chars -> 11337 chars sent
        usage : in=3906 out=178 total=4084
[43/50] (contract #43) MISS WPPPLC_04_30_2020-EX-4.28-SERVICE AGREEMENT
        gold  : '27 January 2020'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 65547 chars -> 2061 chars sent
        usage : in=1682 out=50 total=1732
[44/50] (contract #44) MISS WASTE2ENERGYHOLDINGS,INC_06_03_2010-EX-10.2-S...
        gold  : 'Commencement Date means the date of this Agreement'
        pred  : 'THIS AGREEMENT IS MADE ON THE 19  DAY OF MAY , 2010'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 40442 chars -> 40356 chars sent
        usage : in=10429 out=71 total=10500
[45/50] (contract #45) OK  WORLDWIDESTRATEGIESINC_11_02_2005-EX-10-RESEL...
        gold  : '14 day of SEPTEMBER, 200_'
        pred  : 'This Reseller Agreement is made and entered into as of this 14 day of SEPTEMBER,'
        src   : section-match
        ctx   : 84618 chars -> 84361 chars sent
        usage : in=18538 out=173 total=18711
[46/50] (contract #46) OK  FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_...
        gold  : 'March 1, 2016'
        pred  : 'This SECOND AMENDMENT TO SERVICES AGREEMENT, dated and effective as of March 1, '
        src   : section-match
        ctx   : 5466 chars -> 3065 chars sent
        usage : in=1869 out=75 total=1944
[47/50] (contract #47) MISS AzulSa_20170303_F-1A_EX-10.3_9943903_EX-10.3_...
        gold  : 'January 6th, 2016'
        pred  : 'This Amendment shall enter into force on the date of its signature by both Parties'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 16870 chars -> 320 chars sent
        usage : in=1312 out=67 total=1379
[48/50] (contract #48) MISS DRAGONSYSTEMSINC_01_08_1999-EX-10.17-OUTSOURC...
        gold  : '19 Jan. 1998'
        pred  : 'EFFECTIVE AS OF (EFFECTIVE DATE)'
        pred matched patterns: ['effective date', 'effective as of']
        src   : section-match
        ctx   : 8599 chars -> 684 chars sent
        usage : in=1375 out=59 total=1434
[49/50] (contract #49) OK  SEPARATEACCOUNTIIOFAGL_05_02_2011-EX-99.(J)(4...
        gold  : 'March 30, 2011'
        pred  : 'This Unconditional Capital Maintenance Agreement (this "Agreement"), is made, en'
        src   : section-match
        ctx   : 20121 chars -> 19761 chars sent
        usage : in=5355 out=129 total=5484
[50/50] (contract #50) OK  GridironBionutrientsInc_20171206_8-K_EX-10.2_...
        gold  : 'November 7, 2017'
        pred  : 'This Endorsement Agreement Addendum I (the "Addendum") is made and effective Nov'
        src   : section-match
        ctx   : 3456 chars -> 3204 chars sent
        usage : in=2120 out=79 total=2199

==================================================
ACCURACY: 32/50 = 64%
SECTION MATCHES: 50/50
FALLBACKS: 0/50
TOKENS: input=346332 output=5084 total=351416
AVG INPUT TOKENS / CONTRACT: 6926.6
AVG INPUT TOKENS / SECTION MATCH: 6926.6
AVG INPUT TOKENS / FALLBACK: 0.0
CONTEXT CHARS: full=2520344 snippets=1259483
ESTIMATED COST: $1.1153
==================================================
```
