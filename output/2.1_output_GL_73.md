# Phase 2.1 — Hallucination-rate testing, first validated version (2026-06-24)

**Result: HALLUCINATION RATE 10/73 = 14%** (63/73 = 86% correctly abstained) on the
absent-clause set, alongside **ACCURACY 50/50 = 100%** on the present-clause regression set
— no tradeoff yet at this stage.

## What this version is

Phase 1.3 was only ever tested against the 437 contracts confirmed to *have* a Governing
Law clause. This is the first version that closes that blind spot: it reuses Phase 1.3's
extraction pipeline (`build_candidate_snippets`, section ranking, the windowing fallback)
unchanged, and adds a way to test against the 73 contracts where CUAD confirms the clause
is genuinely absent — measuring whether the pipeline invents a clause when none exists.

Getting to a clean number required two real fixes over the naive reuse of the 1.3 prompt:

- **Free-text formatting leaks.** The original 1.3 prompt ("return an empty response, no
  commentary") still let the model explain itself instead of staying silent — e.g. *"I
  cannot find a governing law clause in the provided excerpt."* That scores as a
  hallucination against an empty gold answer even though the model's underlying judgment
  was correct. Iterating through a forceful "zero characters" instruction landed on an
  explicit sentinel: the model must respond with exactly the word `NONE` when nothing is
  found, which the code then normalizes back to an empty string before scoring.
- **A real regex bug.** The weak keyword pattern `r"venue"` had no word boundary, so it
  matched as a literal substring of "**Avenue**" (e.g. a street address: "625 Fourth Avenue
  South"), causing false section-matches on contracts that had no real governing-law signal
  at all. Fixed to `r"\bvenue\b"`.

## What's left (not fixed by this version)

Of the 10 remaining misses, only 1 (INGEVITYCORP, #71) is a sentinel-detection edge case —
the model wrote a full explanation and then correctly appended `NONE` on its own line at
the end, which the exact-match check didn't catch. The other 9 are the model confidently
mislabeling forum-selection/venue/dispute-resolution clauses as governing law (e.g. "any
disputes shall be settled in a court in Florida"). That confusion is the subject of Phase
2.2 — see [phase2.2_output_hallucination_rate.md](phase2.2_output_hallucination_rate.md).

This version was later superseded by Phase 2.2, which replaced the free-text sentinel with
forced tool use (eliminating the formatting-leak category structurally) and sharpened the
prompt to distinguish governing-law from venue/forum language (fixing 8 of the 9 real
confusions, at the cost of one new miss on the present-clause set). Kept here, unmodified,
as the honest historical snapshot of what "10/73" actually measured.

## Raw run output: absent-clause set, n=73

```
$ python3 phase2.1_governing_law.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --absent --n 73 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 73 contracts with NO Governing Law clause (hallucination-rate check).

[ 1/73] (contract #1) OK  NELNETINC_04_08_2020-EX-1-JOINT FILING AGREEM...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1081 chars -> 1081 chars sent
        usage : in=478 out=5 total=483
[ 2/73] (contract #2) OK  PfHospitalityGroupInc_20150923_10-12G_EX-10.1...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 6772 chars -> 2839 chars sent
        usage : in=866 out=5 total=871
[ 3/73] (contract #3) OK  ThriventVariableInsuranceAccountB_20190701_N-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 4871 chars -> 4871 chars sent
        usage : in=1395 out=5 total=1400
[ 4/73] (contract #4) OK  Freecook_20180605_S-1_EX-10.3_11233807_EX-10....
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 6341 chars -> 6341 chars sent
        usage : in=1641 out=5 total=1646
[ 5/73] (contract #5) MISS GALACTICOMMTECHNOLOGIESINC_11_07_1997-EX-10.4...
        gold  : ''
        pred  : 'Any disputes arising herein shall be settled in a court in FLorida.'
        pred matched patterns: NONE
        src   : full-contract fallback
        ctx   : 1660 chars -> 1660 chars sent
        usage : in=619 out=20 total=639
[ 6/73] (contract #6) OK  PelicanDeliversInc_20200211_S-1_EX-10.3_11975...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16590 chars -> 16590 chars sent
        usage : in=4001 out=5 total=4006
[ 7/73] (contract #7) OK  ORBSATCORP_08_17_2007-EX-7.3-STRATEGIC ALLIAN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 18445 chars -> 13839 chars sent
        usage : in=3279 out=5 total=3284
[ 8/73] (contract #8) OK  GridironBionutrientsInc_20171206_8-K_EX-10.2_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3456 chars -> 3456 chars sent
        usage : in=1209 out=5 total=1214
[ 9/73] (contract #9) OK  VIRGINGALACTICHOLDINGS,INC_04_08_2020-EX-99.1...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1194 chars -> 1194 chars sent
        usage : in=508 out=5 total=513
[10/73] (contract #10) MISS TELEGLOBEINTERNATIONALHOLDINGSLTD_03_29_2004-...
        gold  : ''
        pred  : '27.2 If any difference shall arise between or among the Parties or any of them in respect of the interpretation or effect of this Agreement or any part or provision thereof or their rights and obligations thereunder, and by reasons thereof there shall arise the need to decide the question by what municipal or national law this Agreement or any part or provision thereof is governed, the following facts shall be excluded from consideration, namely that this Agreement was made in a particular country and that it may appear by reason of its form, style, language or otherwise to have been drawn preponderantly with reference to a particular system of municipal or national law; the intention of the Parties being that such facts shall be regarded by the Parties and in all courts and tribunals wherever situated as irrelevant to the question aforesaid and to the decision thereof.'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 94266 chars -> 70916 chars sent
        usage : in=16159 out=173 total=16332
[11/73] (contract #11) MISS NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO ...
        gold  : ''
        pred  : 'This Agreement, including its attachment and order acknowledgments under the Agreement, constitutes the entire agreement between Distributor and NETGEAR with respect to the purchase, resale and distribution of the Products and is governed by the laws of the State of California except that body of law dealing with conflicts of law.'
        pred matched patterns: ['governed by', 'laws of the state']
        src   : section-match
        ctx   : 8113 chars -> 630 chars sent
        usage : in=345 out=66 total=411
[12/73] (contract #12) OK  SECURIANFUNDSTRUST_05_01_2012-EX-99.28.H.9-NE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 9700 chars -> 9700 chars sent
        usage : in=2508 out=5 total=2513
[13/73] (contract #13) OK  BANGIINC_05_25_2005-EX-10-Premium Managed Hos...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2010 chars -> 2010 chars sent
        usage : in=763 out=5 total=768
[14/73] (contract #14) MISS PacificapEntertainmentHoldingsInc_20051115_8-...
        gold  : ''
        pred  : 'ALL DISPUTES ARISING OUT OF THIS AGREEMENT SHALL BE SETTLED VIA BINDING ARBITRATION ACCORDING TO THE RULES AND REGULATIONS SET FORTH BY THE AMERICAN ARBITRATION ASSOCIATION IN SAN DIEGO COUNTY , THE STATE OF CALIFORNIA.'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 18138 chars -> 7029 chars sent
        usage : in=1772 out=58 total=1830
[15/73] (contract #15) OK  RgcResourcesInc_20151216_8-K_EX-10.3_9372751_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5171 chars -> 5171 chars sent
        usage : in=1549 out=5 total=1554
[16/73] (contract #16) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2819 chars -> 2819 chars sent
        usage : in=872 out=5 total=877
[17/73] (contract #17) OK  XLITECHNOLOGIES,INC_12_11_2015-EX-10.1-Sponso...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 18240 chars -> 18240 chars sent
        usage : in=4397 out=5 total=4402
[18/73] (contract #18) OK  SLOVAKWIRELESSFINANCECOBV_03_28_2001-EX-4.(B)...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 33577 chars -> 33577 chars sent
        usage : in=6669 out=5 total=6674
[19/73] (contract #19) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1707 chars -> 1707 chars sent
        usage : in=696 out=5 total=701
[20/73] (contract #20) OK  ArcGroupInc_20171211_8-K_EX-10.1_10976103_EX-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16773 chars -> 16773 chars sent
        usage : in=4054 out=5 total=4059
[21/73] (contract #21) OK  VIVINT SOLAR, INC. - NON-COMPETITION AGREEMEN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3493 chars -> 2349 chars sent
        usage : in=773 out=5 total=778
[22/73] (contract #22) OK  FUSIONPHARMACEUTICALSINC_06_05_2020-EX-10.17-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 40597 chars -> 40583 chars sent
        usage : in=9435 out=5 total=9440
[23/73] (contract #23) OK  SalesforcecomInc_20171122_10-Q_EX-10.1_109615...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2935 chars -> 2935 chars sent
        usage : in=961 out=5 total=966
[24/73] (contract #24) OK  KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVIC...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 7600 chars -> 7600 chars sent
        usage : in=2071 out=5 total=2076
[25/73] (contract #25) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5327 chars -> 5327 chars sent
        usage : in=1476 out=5 total=1481
[26/73] (contract #26) OK  XLITECHNOLOGIES,INC_12_02_2015-EX-10.02-STRAT...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5712 chars -> 5712 chars sent
        usage : in=1528 out=5 total=1533
[27/73] (contract #27) OK  BLACKROCKMUNIHOLDINGSINVESTMENTQUALITYFUND_04...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1283 chars -> 1283 chars sent
        usage : in=521 out=5 total=526
[28/73] (contract #28) OK  RMRGROUPINC_01_22_2020-EX-99.1-JOINT FILING A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 645 chars -> 645 chars sent
        usage : in=414 out=5 total=419
[29/73] (contract #29) OK  CHINARECYCLINGENERGYCORP_11_14_2013-EX-10.6-C...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16509 chars -> 16509 chars sent
        usage : in=3696 out=5 total=3701
[30/73] (contract #30) OK  QBIOMEDINC_04_08_2020-EX-99.1-JOINT FILING AG...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2732 chars -> 2732 chars sent
        usage : in=1131 out=5 total=1136
[31/73] (contract #31) OK  BIOAMBERINC_04_10_2013-EX-10.34-DEVELOPMENT A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 6390 chars -> 6390 chars sent
        usage : in=1887 out=5 total=1892
[32/73] (contract #32) MISS IDREAMSKYTECHNOLOGYLTD_07_03_2014-EX-10.39-Co...
        gold  : ''
        pred  : 'Any disputes between the Parties arising from the performance of this Agreement shall be resolved through amicable negotiations; in case such negotiations fail, both Parties agree to submit the dispute to the competent court where Party A is domiciled.'
        pred matched patterns: NONE
        src   : full-contract fallback
        ctx   : 76425 chars -> 76425 chars sent
        usage : in=16776 out=52 total=16828
[33/73] (contract #33) OK  ONEMAINHOLDINGS,INC_02_20_2020-EX-99.D-JOINT ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5879 chars -> 5879 chars sent
        usage : in=2085 out=5 total=2090
[34/73] (contract #34) OK  NETGEAR,INC_04_21_2003-EX-10.16- AMENDMENT #2...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 4567 chars -> 4567 chars sent
        usage : in=1220 out=5 total=1225
[35/73] (contract #35) OK  SPRINGBANKPHARMACEUTICALS,INC_04_08_2020-EX-9...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1556 chars -> 1556 chars sent
        usage : in=628 out=5 total=633
[36/73] (contract #36) OK  SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3314 chars -> 741 chars sent
        usage : in=385 out=5 total=390
[37/73] (contract #37) OK  UNITEDNATIONALBANCORP_03_03_1999-EX-99-Outsou...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1952 chars -> 1952 chars sent
        usage : in=691 out=5 total=696
[38/73] (contract #38) OK  GALERATHERAPEUTICS,INC_02_14_2020-EX-99.A-JOI...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3892 chars -> 3892 chars sent
        usage : in=1396 out=5 total=1401
[39/73] (contract #39) OK  SOLUTIONSVENDINGINTERNATIONAL,INC_03_31_2020-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 7124 chars -> 7124 chars sent
        usage : in=1820 out=5 total=1825
[40/73] (contract #40) OK  Cerus Corporation - FIRST AMEND TO SUPPLY AND...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11420 chars -> 11420 chars sent
        usage : in=2932 out=5 total=2937
[41/73] (contract #41) OK  OLDAPIWIND-DOWNLTD_01_08_2016-EX-1.3-AGENCY A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3886 chars -> 3886 chars sent
        usage : in=1144 out=5 total=1149
[42/73] (contract #42) OK  ATENTOSA_07_06_2020-EX-99.1-JOINT FILING AGRE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2298 chars -> 2298 chars sent
        usage : in=889 out=5 total=894
[43/73] (contract #43) MISS RISEEDUCATIONCAYMANLTD_04_17_2020-EX-4.23-SER...
        gold  : ''
        pred  : 'The Parties shall seek to resolve all the disputes arising from or in connection with this Agreement through friendly consultation.'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 16372 chars -> 16336 chars sent
        usage : in=3517 out=25 total=3542
[44/73] (contract #44) OK  SPIENERGYCO,LTD_07_10_2014-EX-10-Cooperation ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2811 chars -> 2811 chars sent
        usage : in=832 out=5 total=837
[45/73] (contract #45) OK  WatchitMediaInc_20061201_8-K_EX-10.1_4148672_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2106 chars -> 2106 chars sent
        usage : in=709 out=5 total=714
[46/73] (contract #46) OK  ADMA BioManufacturing, LLC -  Amendment #3 to...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 15312 chars -> 15312 chars sent
        usage : in=4064 out=5 total=4069
[47/73] (contract #47) MISS SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10...
        gold  : ''
        pred  : 'This Guarantee shall be interpreted and construed under the laws of the state in which Franchisor has its principal place of business at the time the action is initiated.'
        pred matched patterns: ['laws of the state']
        src   : section-match
        ctx   : 5504 chars -> 2079 chars sent
        usage : in=696 out=38 total=734
[48/73] (contract #48) OK  MANAKOASERVICESCORP_11_21_2007-EX-7.5-STRATEG...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 14879 chars -> 14864 chars sent
        usage : in=3538 out=5 total=3543
[49/73] (contract #49) OK  BizzingoInc_20120322_8-K_EX-10.17_7504499_EX-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 24223 chars -> 3713 chars sent
        usage : in=1062 out=5 total=1067
[50/73] (contract #50) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 8024 chars -> 8024 chars sent
        usage : in=2151 out=5 total=2156
[51/73] (contract #51) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3422 chars -> 3422 chars sent
        usage : in=1184 out=5 total=1189
[52/73] (contract #52) OK  MFAFINANCIAL,INC_07_06_2020-EX-99.D-JOINT FIL...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3595 chars -> 3595 chars sent
        usage : in=1268 out=5 total=1273
[53/73] (contract #53) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11954 chars -> 11954 chars sent
        usage : in=3315 out=5 total=3320
[54/73] (contract #54) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2274 chars -> 2274 chars sent
        usage : in=789 out=5 total=794
[55/73] (contract #55) OK  UnionDentalHoldingsInc_20050204_8-KA_EX-10_33...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 14083 chars -> 12949 chars sent
        usage : in=3153 out=5 total=3158
[56/73] (contract #56) OK  WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-EN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 7042 chars -> 2809 chars sent
        usage : in=760 out=5 total=765
[57/73] (contract #57) OK  PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3558 chars -> 3558 chars sent
        usage : in=1089 out=5 total=1094
[58/73] (contract #58) MISS ZtoExpressCaymanInc_20160930_F-1_EX-10.10_975...
        gold  : ''
        pred  : "Any dispute arising out of the execution of this Agreement, which cannot be negotiated and settled by both Parties, shall be subject to the jurisdiction of the People's Court where this Agreement is signed."
        pred matched patterns: ['jurisdiction']
        src   : section-match
        ctx   : 9174 chars -> 1255 chars sent
        usage : in=505 out=43 total=548
[59/73] (contract #59) OK  ScansourceInc_20190822_10-K_EX-10.39_11793959...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 10891 chars -> 2745 chars sent
        usage : in=860 out=5 total=865
[60/73] (contract #60) OK  PcquoteComInc_19990721_S-1A_EX-10.11_6377149_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 857 chars -> 857 chars sent
        usage : in=488 out=5 total=493
[61/73] (contract #61) OK  MACY_S,INC_05_11_2020-EX-99.4-JOINT FILING AG...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 1397 chars -> 1162 chars sent
        usage : in=506 out=5 total=511
[62/73] (contract #62) OK  PcquoteComInc_19990721_S-1A_EX-10.11_6377149_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2558 chars -> 2558 chars sent
        usage : in=872 out=5 total=877
[63/73] (contract #63) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1902 chars -> 1902 chars sent
        usage : in=716 out=5 total=721
[64/73] (contract #64) OK  IMAGEWARESYSTEMSINC_12_20_1999-EX-10.22-MAINT...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 21778 chars -> 7981 chars sent
        usage : in=1932 out=5 total=1937
[65/73] (contract #65) OK  ZONDWINDSYSTEMPARTNERSLTDSERIES85-B_04_03_200...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 17712 chars -> 17712 chars sent
        usage : in=3140 out=5 total=3145
[66/73] (contract #66) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1742 chars -> 1742 chars sent
        usage : in=644 out=5 total=649
[67/73] (contract #67) OK  PRECIGEN,INC_01_22_2020-EX-99.1-JOINT FILING ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 972 chars -> 972 chars sent
        usage : in=577 out=5 total=582
[68/73] (contract #68) MISS PhotronicsInc_20171219_10-QA_EX-10.28_1098265...
        gold  : ''
        pred  : 'Section 12 (Miscellaneous) of the China JV Operating Agreement shall be incorporated by reference into and form an integral part of this Agreement, mutatis mutandis.'
        pred matched patterns: NONE
        src   : section-match
        ctx   : 25392 chars -> 3949 chars sent
        usage : in=1195 out=41 total=1236
[69/73] (contract #69) OK  ALCOSTORESINC_12_14_2005-EX-10.26-AGENCY AGRE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11355 chars -> 11355 chars sent
        usage : in=2783 out=5 total=2788
[70/73] (contract #70) OK  NETZEEINC_11_14_2002-EX-10.3-MAINTENANCE AGRE...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3474 chars -> 3446 chars sent
        usage : in=985 out=5 total=990
[71/73] (contract #71) MISS INGEVITYCORP_05_16_2016-EX-10.5-INTELLECTUAL ...
        gold  : ''
        pred  : 'Based on the excerpts provided, I can see that excerpt 4 references the governing law clause but does not contain the actual text. It states:\n\n"The terms and conditions set forth in Section 10.2 (Governing Law) through Section 10.19 (Mutual Drafting) of the Separation Agreement are hereby incorporated into this Section 8 as if fully set forth herein."\n\nHowever, the actual text of Section 10.2 (Governing Law) from the Separation Agreement is not provided in any of the four excerpts.\n\nNONE'
        pred matched patterns: ['governing law']
        src   : section-match
        ctx   : 63376 chars -> 5051 chars sent
        usage : in=1404 out=127 total=1531
[72/73] (contract #72) OK  NOVOINTEGRATEDSCIENCES,INC_12_23_2019-EX-10.1...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 21955 chars -> 5916 chars sent
        usage : in=1549 out=5 total=1554
[73/73] (contract #73) OK  TALLGRASSENERGY,LP_02_20_2020-EX-99.26-JOINT ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3971 chars -> 3971 chars sent
        usage : in=1334 out=5 total=1339

==================================================
HALLUCINATION RATE: 10/73 = 14%
CORRECTLY ABSTAINED: 63/73 = 86%
SECTION MATCHES: 22/73
FALLBACKS: 51/73
TOKENS: input=155256 output=958 total=156214
AVG INPUT TOKENS / CONTRACT: 2126.8
AVG INPUT TOKENS / SECTION MATCH: 2485.3
AVG INPUT TOKENS / FALLBACK: 1972.2
CONTEXT CHARS: full=820125 snippets=610628
ESTIMATED COST: $0.4801
==================================================
```

## Raw run output: present-clause regression check, n=50 (same code, confirms no tradeoff yet)

```
$ python3 phase2.1_governing_law.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --n 50 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 50 contracts that have a Governing Law clause.

[ 1/50] (contract #1) OK  LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGR...
        gold  : 'This Agreement is to be construed according to the laws          of the State of'
        pred  : 'This Agreement is to be construed according to the laws of the State of Illinois'
        src   : section-match
        ctx   : 54290 chars -> 6243 chars sent
        usage : in=1659 out=20 total=1679
[ 2/50] (contract #2) OK  WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION ...
        gold  : 'This Agreement is governed by English law and the parties submit to the exclusiv'
        pred  : 'This Agreement is governed by English law and the parties submit to the exclusiv'
        src   : section-match
        ctx   : 70383 chars -> 31973 chars sent
        usage : in=7275 out=63 total=7338
[ 3/50] (contract #3) OK  LohaCompanyltd_20191209_F-1_EX-10.16_11917878...
        gold  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        pred  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        src   : section-match
        ctx   : 11475 chars -> 1321 chars sent
        usage : in=517 out=36 total=553
[ 4/50] (contract #4) OK  CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-W...
        gold  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        pred  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        src   : section-match
        ctx   : 15176 chars -> 2586 chars sent
        usage : in=749 out=53 total=802
[ 5/50] (contract #5) OK  ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT ...
        gold  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        pred  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        src   : section-match
        ctx   : 24632 chars -> 112 chars sent
        usage : in=242 out=21 total=263
[ 6/50] (contract #6) OK  KIROMICBIOPHARMA,INC_05_11_2020-EX-10.23-CONS...
        gold  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        pred  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        src   : section-match
        ctx   : 18403 chars -> 17065 chars sent
        usage : in=3765 out=26 total=3791
[ 7/50] (contract #7) OK  VEONEER,INC_02_21_2020-EX-10.11-JOINT VENTURE...
        gold  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        pred  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 8257 chars -> 8211 chars sent
        usage : in=2564 out=20 total=2584
[ 8/50] (contract #8) OK  DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_...
        gold  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        pred  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        src   : section-match
        ctx   : 175580 chars -> 12116 chars sent
        usage : in=3005 out=71 total=3076
[ 9/50] (contract #9) OK  PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...
        gold  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        pred  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        src   : section-match
        ctx   : 145168 chars -> 119404 chars sent
        usage : in=28109 out=72 total=28181
[10/50] (contract #10) OK  MetLife, Inc. - Remarketing Agreement
        gold  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        pred  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        src   : section-match
        ctx   : 111249 chars -> 98213 chars sent
        usage : in=21625 out=79 total=21704
[11/50] (contract #11) OK  FTENETWORKS,INC_02_18_2016-EX-99.4-STRATEGIC ...
        gold  : 'The construction, interpretation, and performance of this Agreement and all tran'
        pred  : 'The construction, interpretation, and performance of this Agreement and all tran'
        src   : section-match
        ctx   : 37829 chars -> 5886 chars sent
        usage : in=1516 out=40 total=1556
[12/50] (contract #12) OK  DOMINIADVISORTRUST_02_18_2005-EX-99.(H)(2)-SP...
        gold  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        pred  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        src   : full-contract fallback
        ctx   : 12555 chars -> 12555 chars sent
        usage : in=2725 out=36 total=2761
[13/50] (contract #13) OK  CerenceInc_20191002_8-K_EX-10.4_11827494_EX-1...
        gold  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        pred  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        src   : section-match
        ctx   : 62170 chars -> 19318 chars sent
        usage : in=4663 out=64 total=4727
[14/50] (contract #14) OK  ReynoldsConsumerProductsInc_20191115_S-1_EX-1...
        gold  : 'This Agreement and all claims or causes of action arising out of or related to t'
        pred  : 'This Agreement and all claims or causes of action arising out of or related to t'
        src   : section-match
        ctx   : 61710 chars -> 60691 chars sent
        usage : in=12994 out=65 total=13059
[15/50] (contract #15) OK  IntegrityFunds_20200121_485BPOS_EX-99.E UNDR ...
        gold  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        pred  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        src   : section-match
        ctx   : 23845 chars -> 1239 chars sent
        usage : in=490 out=20 total=510
[16/50] (contract #16) OK  PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTEL...
        gold  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        pred  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        src   : section-match
        ctx   : 23282 chars -> 1681 chars sent
        usage : in=550 out=56 total=606
[17/50] (contract #17) OK  SIBANNAC,INC_12_04_2017-EX-2.1-Strategic Alli...
        gold  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        pred  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        src   : section-match
        ctx   : 8380 chars -> 2336 chars sent
        usage : in=791 out=27 total=818
[18/50] (contract #18) OK  INTRICONCORP_03_10_2009-EX-10.22-Strategic Al...
        gold  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        pred  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        src   : section-match
        ctx   : 52967 chars -> 26862 chars sent
        usage : in=6517 out=29 total=6546
[19/50] (contract #19) OK  BONTONSTORESINC_04_20_2018-EX-99.3-AGENCY AGR...
        gold  : 'This Agreement shall be governed by and interpreted in accordance with the laws '
        pred  : '# GOVERNING LAW CLAUSE\n\nThis Agreement shall be governed by and interpreted in a'
        src   : section-match
        ctx   : 161626 chars -> 111089 chars sent
        usage : in=25964 out=48 total=26012
[20/50] (contract #20) OK  ON2TECHNOLOGIES,INC_11_17_2006-EX-10.3-SUPPOR...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : '10.7 Governing Law; Forum. This Agreement shall be governed by and construed in '
        src   : section-match
        ctx   : 61392 chars -> 39313 chars sent
        usage : in=9124 out=68 total=9192
[21/50] (contract #21) OK  OPERALTD_04_30_2020-EX-4.14-SERVICE AGREEMENT
        gold  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        pred  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        src   : section-match
        ctx   : 20983 chars -> 2987 chars sent
        usage : in=877 out=45 total=922
[22/50] (contract #22) OK  BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT V...
        gold  : 'By this Agreement the Members enter into a joint venture (the "Venture") in acco'
        pred  : 'The Members submit to the jurisdiction of the courts of the State of Florida for'
        src   : section-match
        ctx   : 21450 chars -> 4646 chars sent
        usage : in=1197 out=36 total=1233
[23/50] (contract #23) OK  ZEBRATECHNOLOGIESCORP_04_16_2014-EX-10.1-INTE...
        gold  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        pred  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        src   : section-match
        ctx   : 127205 chars -> 40538 chars sent
        usage : in=9375 out=56 total=9431
[24/50] (contract #24) OK  ChinaRealEstateInformationCorp_20090929_F-1_E...
        gold  : 'This Termination Agreement shall be governed by the laws of the PRC, without reg'
        pred  : 'This Agreement and any dispute or claim arising out of or in connection with it '
        src   : section-match
        ctx   : 49191 chars -> 15454 chars sent
        usage : in=3864 out=64 total=3928
[25/50] (contract #25) OK  HERTZGLOBALHOLDINGS,INC_07_07_2016-EX-10.4-IN...
        gold  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        pred  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        src   : section-match
        ctx   : 30968 chars -> 30554 chars sent
        usage : in=7759 out=74 total=7833
[26/50] (contract #26) OK  GLOBALTECHNOLOGIESLTD_06_08_2020-EX-10.16-CON...
        gold  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        pred  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        src   : section-match
        ctx   : 20805 chars -> 4084 chars sent
        usage : in=1037 out=42 total=1079
[27/50] (contract #27) OK  PfHospitalityGroupInc_20150923_10-12G_EX-10.1...
        gold  : 'This Agreement and the relationship between the parties is governed by and will '
        pred  : 'This Agreement and the relationship between the parties is governed by and will '
        src   : section-match
        ctx   : 152649 chars -> 5010 chars sent
        usage : in=1500 out=47 total=1547
[28/50] (contract #28) OK  CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTI...
        gold  : 'This Agreement shall be governed by         the laws of the State of California,'
        pred  : 'This Agreement shall be governed by the laws of the State of California, USA, ex'
        src   : section-match
        ctx   : 62324 chars -> 52814 chars sent
        usage : in=11125 out=45 total=11170
[29/50] (contract #29) OK  TUNIUCORP_03_06_2014-EX-10-COOPERATION AGREEM...
        gold  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        pred  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        src   : section-match
        ctx   : 17917 chars -> 17903 chars sent
        usage : in=4046 out=71 total=4117
[30/50] (contract #30) OK  CYBERIANOUTPOSTINC_07_09_1998-EX-10.13-PROMOT...
        gold  : 'This Agreement will be construed in accordance with           and governed by th'
        pred  : 'This Agreement will be construed in accordance with and governed by the laws of '
        src   : section-match
        ctx   : 25288 chars -> 23373 chars sent
        usage : in=5172 out=33 total=5205
[31/50] (contract #31) OK  SENMIAOTECHNOLOGYLTD_02_19_2019-EX-10.5-Colla...
        gold  : 'The execution, validation, interpretation, performance, modification and termina'
        pred  : 'The execution, validation, interpretation, performance, modification and termina'
        src   : section-match
        ctx   : 73890 chars -> 1412 chars sent
        usage : in=511 out=36 total=547
[32/50] (contract #32) OK  HealthcareIntegratedTechnologiesInc_20190812_...
        gold  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        pred  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        src   : section-match
        ctx   : 22288 chars -> 2854 chars sent
        usage : in=761 out=89 total=850
[33/50] (contract #33) OK  LOYALTYPOINTINC_11_16_2004-EX-10.2-RESELLER A...
        gold  : 'This Agreement shall be subject to and governed by the laws of the          Stat'
        pred  : 'This Agreement shall be deemed to have been made and executed in the State of Mi'
        src   : section-match
        ctx   : 117478 chars -> 23340 chars sent
        usage : in=4801 out=49 total=4850
[34/50] (contract #34) OK  BNCMORTGAGEINC_05_17_1999-EX-10.4-LICENSING A...
        gold  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        pred  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        src   : section-match
        ctx   : 32680 chars -> 19062 chars sent
        usage : in=4138 out=33 total=4171
[35/50] (contract #35) OK  ENERGOUSCORP_03_16_2017-EX-10.24-STRATEGIC AL...
        gold  : 'This Letter of Authorization will be governed by and construed in accordance wit'
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 81926 chars -> 9809 chars sent
        usage : in=2372 out=30 total=2402
[36/50] (contract #36) OK  CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-...
        gold  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        pred  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        src   : section-match
        ctx   : 159488 chars -> 10552 chars sent
        usage : in=2585 out=63 total=2648
[37/50] (contract #37) OK  MSCIINC_02_28_2008-EX-10.10-
        gold  : 'This Agreement shall be construed in accordance with and governed by the substan'
        pred  : 'This Agreement shall be construed in accordance with and governed by the substan'
        src   : section-match
        ctx   : 11770 chars -> 9056 chars sent
        usage : in=2333 out=27 total=2360
[38/50] (contract #38) OK  NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEME...
        gold  : 'This Agreement shall be governed by and           construed in accordance with t'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 148163 chars -> 41924 chars sent
        usage : in=8866 out=32 total=8898
[39/50] (contract #39) OK  ImpresseCorp_20000322_S-1A_EX-10.11_5199234_E...
        gold  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        pred  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        src   : section-match
        ctx   : 47639 chars -> 16827 chars sent
        usage : in=4047 out=28 total=4075
[40/50] (contract #40) OK  AlliedEsportsEntertainmentInc_20190815_8-K_EX...
        gold  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        pred  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        src   : section-match
        ctx   : 35504 chars -> 6728 chars sent
        usage : in=1811 out=45 total=1856
[41/50] (contract #41) OK  CHERRYHILLMORTGAGEINVESTMENTCORP_09_26_2013-E...
        gold  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        pred  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        src   : section-match
        ctx   : 27741 chars -> 27624 chars sent
        usage : in=6201 out=47 total=6248
[42/50] (contract #42) OK  CreditcardscomInc_20070810_S-1_EX-10.33_36229...
        gold  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        pred  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        src   : section-match
        ctx   : 28804 chars -> 1531 chars sent
        usage : in=664 out=28 total=692
[43/50] (contract #43) OK  Zounds Hearing, Inc. - MANUFACTURING DESIGN M...
        gold  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        pred  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        src   : section-match
        ctx   : 47001 chars -> 3198 chars sent
        usage : in=884 out=62 total=946
[44/50] (contract #44) OK  CUROGROUPHOLDINGSCORP_05_04_2020-EX-10.3-SERV...
        gold  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        pred  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        src   : section-match
        ctx   : 36602 chars -> 34031 chars sent
        usage : in=7846 out=96 total=7942
[45/50] (contract #45) OK  SouthernStarEnergyInc_20051202_SB-2A_EX-9_801...
        gold  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        pred  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        src   : section-match
        ctx   : 22721 chars -> 1859 chars sent
        usage : in=653 out=32 total=685
[46/50] (contract #46) OK  ConformisInc_20191101_10-Q_EX-10.6_11861402_E...
        gold  : 'This Agreement shall be governed and construed in accordance with the laws of Ne'
        pred  : '10.7 Governing Law. This Agreement shall be governed and construed in accordance'
        src   : section-match
        ctx   : 63217 chars -> 8801 chars sent
        usage : in=2234 out=40 total=2274
[47/50] (contract #47) OK  Principal Life Insurance Company - Broker Dea...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 29599 chars -> 9458 chars sent
        usage : in=2292 out=23 total=2315
[48/50] (contract #48) OK  LegacyEducationAllianceInc_20200330_10-K_EX-1...
        gold  : 'This Agreement will be governed by and construed in accordance with the laws of '
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 46255 chars -> 9188 chars sent
        usage : in=2411 out=55 total=2466
[49/50] (contract #49) OK  VerizonAbsLlc_20200123_8-K_EX-10.4_11952335_E...
        gold  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        pred  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        src   : section-match
        ctx   : 289615 chars -> 63749 chars sent
        usage : in=15149 out=99 total=15248
[50/50] (contract #50) OK  VERICELCORP_08_06_2019-EX-10.10-SUPPLY AGREEM...
        gold  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        pred  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        src   : section-match
        ctx   : 102006 chars -> 10220 chars sent
        usage : in=2536 out=47 total=2583

==================================================
ACCURACY: 50/50 = 100%
SECTION MATCHES: 49/50
FALLBACKS: 1/50
TOKENS: input=253891 output=2388 total=256279
AVG INPUT TOKENS / CONTRACT: 5077.8
AVG INPUT TOKENS / SECTION MATCH: 5125.8
AVG INPUT TOKENS / FALLBACK: 2725.0
CONTEXT CHARS: full=3093536 snippets=1086800
ESTIMATED COST: $0.7975
==================================================
```
