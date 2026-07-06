# Phase 3.3 — Effective Date extraction, n=50 (2026-07-01)

**Result: ACCURACY 38/50 = 76%** | input tokens 450,817 | estimated cost $1.4306

Up from 74% (37/50) in phase 3.2 — one additional contract recovered as an unintentional
side effect of the refactor described below. Of the 12 remaining misses, 5 are confirmed
scorer-vs-substance gaps, raising the true extraction accuracy to **43/50 = 86%**.

## What changed from 3.2 — single-pass section scan refactor

Phase 3.2 made two passes over the contract text for every extraction:
1. `build_section_spans()` walked all lines to detect header boundaries and build section spans
2. `build_candidate_snippets()` walked all lines *again* to find keyword matches and assign
   tiers to sections

These are now merged into one function, `_scan_sections_and_keywords()`, which does both
simultaneously by tracking the current open section as it goes:

```
for each line:
    if line is a header:
        close current section → add to section_spans
        open new section with this line as header
    if line matches any EFFECTIVE_DATE_PATTERN:
        attribute to current open section (index = len(section_spans))
        compute tier using current section's header
        update section_best_tier
close final section
```

This eliminates the inner `for section_idx in section_spans` lookup loop that previously ran
inside every keyword-matched line, reduces each contract to a single O(n) pass, and
naturally produces the same section structure — including the preamble-orphaning fix (text
before the first header becomes section 0) — without an extra pre-scan.

`build_section_spans()` is removed; `build_candidate_snippets()` and
`diagnose_section_candidates()` both now call `_scan_sections_and_keywords()` instead of
duplicating the scan logic independently.

## Unexpected improvement from the windowing-trigger fix

The refactor also changed the windowing path trigger from `len(section_spans) <= 1` to
`not has_sections`. These are subtly different:

- **Old trigger:** fired when only 0 or 1 header was detected (0-header = no spans; 1
  header at offset 0 = one span covering the whole document).
- **New trigger:** fires only when NO header lines were detected at all.

For documents with exactly 1 header at offset 0, the old code used the windowing path
(sending 100-word windows around keyword matches). The new code uses section-based
selection instead — which, for those documents, results in the relevant section content
being sent correctly rather than potentially-wrong windowed neighborhoods.

**Contract #38 (SouthernStarEnergyInc)** is the concrete case: it had one header at the
document start, causing windowing that produced 8 incorrect windows none of which contained
the gold clause. With section-based selection now active, the full contract is sent as a
single section, the model sees the gold clause, and returns it verbatim:

- Gold: `"The term of this Agreement will begin upon acceptance of Affiliate's Program application..."`
- Pred: `"The term of this Agreement will begin upon acceptance of Affiliate's Program application..."` ✓

This is also a notable extraction: there is no calendar date in this clause at all — it's
event-conditional. The model correctly identified and quoted the commencement-condition
clause as the effective-date declaration rather than inventing a date.

## Token cost note

Input tokens rose from 392,909 (phase 3.2) to 450,817 (phase 3.3) — a ~15% increase. The
more precise windowing trigger means several documents that previously got small keyword
windows now get full or larger sections, which is more accurate but costs more. This is
the correct direction for an extraction system: correctness before cost reduction.

## Remaining misses — categorized

**Scorer-vs-substance gaps (5) — model substantively correct:**
- #7, #10, #11, #24, #44 — same as phase 3.2 (see phase3.2 output doc for details)

**Structural/unfixable (4):**
- #40 (Principal Life): blank template date (`"this ______ day of _____"`)
- #43 (WPPPLC): "Appointment" terminology + wrong section selected
- #47, #48: Category C — correct tier-2 header selected but date value in different section

**Genuine extraction failures (3):**
- #6: event-conditional amendment (model finds the execution date instead)
- #25: execution date January 26 found instead of Term commencement February 1
- #26: model returns a procedural effectiveness clause instead of the bare date `"December 17, 2018"`

## Raw run output, n=50

```
$ python3 phase3.3_effective_date.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --n 50 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 50 contracts that have an Effective Date clause.

[ 1/50] (contract #1) OK  LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGR...
        gold  : 'The term of this  Agreement  shall be ten (10)                            years '
        pred  : 'The term of this  Agreement  shall be ten (10)                            years '
        src   : section-match
        ctx   : 54290 chars -> 15622 chars sent
        usage : in=4553 out=106 total=4659
[ 2/50] (contract #2) OK  WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION ...
        gold  : '1 August 2011'
        pred  : 'This Promotion and Distribution Agreement including all exhibits (collectively r'
        src   : section-match
        ctx   : 70383 chars -> 57559 chars sent
        usage : in=14648 out=172 total=14820
[ 3/50] (contract #3) OK  CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-W...
        gold  : 'The term of this Agreement for the Hosted Site shall commence upon April 1, 1999'
        pred  : 'The term of this Agreement for the Hosted Site shall commence upon April 1, 1999'
        src   : section-match
        ctx   : 15176 chars -> 905 chars sent
        usage : in=1425 out=71 total=1496
[ 4/50] (contract #4) OK  ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT ...
        gold  : 'The Term of this Agreement shall be for a period of [* ****] years and [*****] m'
        pred  : 'The Term of this Agreement shall be for a period of [* ****] years and [*****] m'
        src   : section-match
        ctx   : 24632 chars -> 193 chars sent
        usage : in=1285 out=86 total=1371
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
        ctx   : 175580 chars -> 130876 chars sent
        usage : in=31219 out=84 total=31303
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
        ctx   : 37829 chars -> 37829 chars sent
        usage : in=9591 out=92 total=9683
[10/50] (contract #10) MISS DOMINIADVISORTRUST_02_18_2005-EX-99.(H)(2)-SP...
        gold  : 'This Agreement shall become effective as of the day and year first above written...'
        pred  : 'SPONSORSHIP AGREEMENT, dated as of February 4, 2005...'
        pred matched patterns: ['dated as of', ...]
        src   : section-match
        ctx   : 12555 chars -> 11832 chars sent
        usage : in=3647 out=106 total=3753
[11/50] (contract #11) MISS CerenceInc_20191002_8-K_EX-10.4_11827494_EX-1...
        gold  : 'This Agreement may be executed in one or more counterparts...shall become effective when signed...'
        pred  : 'INTELLECTUAL PROPERTY AGREEMENT, dated as of September 30, 2019 (this "Agreement")...'
        pred matched patterns: ['dated as of', ...]
        src   : section-match
        ctx   : 62170 chars -> 24647 chars sent
        usage : in=7079 out=110 total=7189
[12/50] (contract #12) OK  ThriventVariableInsuranceAccountB_20190701_N-...
        gold  : 'July 1, 2019'
        pred  : 'Effective Date: July 1, 2019'
        src   : section-match
        ctx   : 4871 chars -> 2877 chars sent
        usage : in=1892 out=62 total=1954
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
        ctx   : 23282 chars -> 23282 chars sent
        usage : in=6505 out=78 total=6583
[15/50] (contract #15) OK  INTRICONCORP_03_10_2009-EX-10.22-Strategic Al...
        gold  : '1st day of October, 2008'
        pred  : 'This Agreement is entered into and is effective as of the 1st day of October, 20'
        src   : section-match
        ctx   : 52967 chars -> 47315 chars sent
        usage : in=12119 out=79 total=12198
[16/50] (contract #16) OK  ON2TECHNOLOGIES,INC_11_17_2006-EX-10.3-SUPPOR...
        gold  : 'April __, 2005'
        pred  : 'SUPPORT AND MAINTENANCE AGREEMENT dated as of April __, 2005 (the "Effective Dat'
        src   : section-match
        ctx   : 61392 chars -> 50980 chars sent
        usage : in=12903 out=105 total=13008
[17/50] (contract #17) OK  OPERALTD_04_30_2020-EX-4.14-SERVICE AGREEMENT
        gold  : 'April. 1st 2019'
        pred  : 'This Service Agreement ("Agreement") is entered into on April. 1st 2019 ("Effect'
        src   : section-match
        ctx   : 20983 chars -> 20983 chars sent
        usage : in=5921 out=75 total=5996
[18/50] (contract #18) OK  BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT V...
        gold  : 'The duration of this Venture (the "Term") will begin on March 1, 2020 and contin'
        pred  : 'The duration of this Venture (the "Term") will begin on March 1, 2020'
        src   : section-match
        ctx   : 21450 chars -> 21450 chars sent
        usage : in=5814 out=72 total=5886
[19/50] (contract #19) OK  ZEBRATECHNOLOGIESCORP_04_16_2014-EX-10.1-INTE...
        gold  : 'April 14, 2014'
        pred  : 'THIS INTELLECTUAL PROPERTY AGREEMENT (this "IP Agreement") is entered into as of'
        src   : section-match
        ctx   : 127205 chars -> 87508 chars sent
        usage : in=21262 out=120 total=21382
[20/50] (contract #20) OK  ChinaRealEstateInformationCorp_20090929_F-1_E...
        gold  : '"Effective Date" means the Closing Date as set forth in the Share Purchase Agree'
        pred  : '"Effective Date" means the Closing Date as set forth in the Share Purchase Agree'
        src   : section-match
        ctx   : 49191 chars -> 40434 chars sent
        usage : in=10735 out=69 total=10804
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
        ctx   : 20805 chars -> 20805 chars sent
        usage : in=5580 out=77 total=5657
[23/50] (contract #23) OK  CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTI...
        gold  : 'October 29, 1999'
        pred  : 'This License and Hosting Agreement (the "AGREEMENT") is made and entered into as'
        src   : section-match
        ctx   : 62324 chars -> 55843 chars sent
        usage : in=12792 out=165 total=12957
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
        ctx   : 117478 chars -> 28803 chars sent
        usage : in=6967 out=72 total=7039
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
        ctx   : 81926 chars -> 81926 chars sent
        usage : in=19468 out=83 total=19551
[31/50] (contract #31) OK  CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-...
        gold  : 'December 17, 2019'
        pred  : 'This Commercialization and License Agreement (this "Agreement") is made effectiv'
        src   : section-match
        ctx   : 159488 chars -> 116949 chars sent
        usage : in=28473 out=122 total=28595
[32/50] (contract #32) OK  MSCIINC_02_28_2008-EX-10.10-
        gold  : 'November 20, 2007'
        pred  : 'This Intellectual Property Agreement (the "Agreement"), is entered into as of No'
        src   : section-match
        ctx   : 11770 chars -> 2674 chars sent
        usage : in=1837 out=112 total=1949
[33/50] (contract #33) OK  NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEME...
        gold  : 'January 21st, 2002'
        pred  : 'This Manufacturing Outsourcing Agreement (The "AGREEMENT") is entered into on Ja'
        src   : section-match
        ctx   : 148163 chars -> 87292 chars sent
        usage : in=18302 out=206 total=18508
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
        ctx   : 35504 chars -> 35504 chars sent
        usage : in=9603 out=251 total=9854
[36/50] (contract #36) OK  CreditcardscomInc_20070810_S-1_EX-10.33_36229...
        gold  : 'The term of this Agreement will commence on the date that the Affiliate Registra'
        pred  : 'The term of this Agreement will commence on the date that the Affiliate Registra'
        src   : section-match
        ctx   : 28804 chars -> 28804 chars sent
        usage : in=7553 out=71 total=7624
[37/50] (contract #37) OK  Zounds Hearing, Inc. - MANUFACTURING DESIGN M...
        gold  : 'October 3, 2018'
        pred  : 'This MANUFACTURING, DESIGN AND MARKETING AGREEMENT (this "Agreement") is entered'
        src   : section-match
        ctx   : 47001 chars -> 47001 chars sent
        usage : in=11197 out=129 total=11326
[38/50] (contract #38) OK  SouthernStarEnergyInc_20051202_SB-2A_EX-9_801...
        gold  : "The term of this Agreement will begin upon acceptance of Affiliate's Program app"
        pred  : "The term of this Agreement will begin upon acceptance of Affiliate's Program app"
        src   : section-match
        ctx   : 22721 chars -> 22721 chars sent
        usage : in=6103 out=77 total=6180
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
        ctx   : 46255 chars -> 46255 chars sent
        usage : in=12264 out=136 total=12400
[42/50] (contract #42) OK  VERICELCORP_08_06_2019-EX-10.10-SUPPLY AGREEM...
        gold  : 'May 6, 2019'
        pred  : 'THIS SUPPLY AGREEMENT (the "Agreement") is entered into as of May 6, 2019 (the "'
        src   : section-match
        ctx   : 102006 chars -> 23770 chars sent
        usage : in=6860 out=178 total=7038
[43/50] (contract #43) MISS WPPPLC_04_30_2020-EX-4.28-SERVICE AGREEMENT
        gold  : '27 January 2020'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 65547 chars -> 20832 chars sent
        usage : in=5921 out=50 total=5971
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
        ctx   : 3456 chars -> 3456 chars sent
        usage : in=2219 out=79 total=2298

==================================================
ACCURACY: 38/50 = 76%
SECTION MATCHES: 50/50
FALLBACKS: 0/50
TOKENS: input=450817 output=5212 total=456029
AVG INPUT TOKENS / CONTRACT: 9016.3
AVG INPUT TOKENS / SECTION MATCH: 9016.3
AVG INPUT TOKENS / FALLBACK: 0.0
CONTEXT CHARS: full=2520344 snippets=1737070
ESTIMATED COST: $1.4306
==================================================
```
