# Phase 2.2 — Hallucination-rate testing, tool use + sharpened prompt (2026-06-24)

**Result: HALLUCINATION RATE 2/73 = 3%** (71/73 = 97% correctly abstained) on the
absent-clause set, alongside **ACCURACY 49/50 = 98%** on the present-clause regression set
(down 1 from Phase 2.1's 100% — see "The tradeoff" below).

Builds directly on
[Phase 2.1](phase2.1_output_hallucination_rate.md) (14% hallucination rate, 100%
present-clause accuracy). Two changes on top of that baseline:

## What changed from 2.1

- **Forced tool use instead of free-text sentinel parsing.** 2.1's free-text `NONE`
  sentinel still leaked in edge cases — e.g. contract #71 (INGEVITYCORP), where the model
  wrote a full explanation and only appended `NONE` on its own line at the end, which the
  exact-match check didn't catch. Rather than keep patching string-matching heuristics, the
  model now must call a `report_governing_law(found: bool, clause_text: str)` tool with a
  forced `tool_choice`. There's no free-text wrapper for commentary to leak through, and
  `found` is read directly off a typed field instead of being inferred from whether a string
  happens to be empty.
- **Sharpened the prompt to explicitly distinguish governing-law clauses from
  forum/venue/dispute-resolution clauses.** Once formatting noise was eliminated, the
  remaining 2.1 misses were a real, consistent pattern: the model confidently mislabeling
  forum-selection language as governing law (e.g. *"any disputes shall be settled in a
  court in Florida"*, *"the parties submit to the exclusive jurisdiction of the courts of
  New York"*). These are legally distinct from a choice-of-law clause but textually
  similar, and the prompt's definition didn't draw that line. Adding an explicit
  contrastive instruction fixed all 8 confirmed instances of this confusion.

## The tradeoff

The same sharper distinction caused one new miss on the present-clause set. BorrowMoney's
CUAD-labeled answer — *"By this Agreement the Members enter into a joint venture... in
accordance with the laws of the State of Florida"* — is structurally almost identical to
the entity-*formation* language Phase 1.3 had already taught the model to reject (recall
the Verizon case: "validly existing... under the laws of the State of Delaware" was
correctly filtered out as formation language, not governing law). Sharpening the
venue/governing-law boundary pushed the model to read BorrowMoney's clause the same way,
even though CUAD labels it as governing law. This is a genuine precision/recall tradeoff on
a contract that sits right on an ambiguous boundary, not a bug — accepted and documented
rather than chased further.

## What's left in the absent-clause set (not model errors)

The 2 remaining absent-clause misses are not extraction failures:

- **NETGEAR** (contract #11): CUAD splits one legal filing into three separate "contracts"
  (a base Distributor Agreement plus two Amendments). The base agreement has a labeled
  Governing Law answer; the model found that exact clause's text while processing one of
  the *unlabeled* Amendments, which apparently shares/reproduces the same underlying text.
  The model is arguably right; CUAD's per-document labeling convention disagrees.
- **SoupmanInc** (contract #47): a "Guarantee" document whose governing law is a *variable*
  jurisdiction ("the state in which Franchisor has its principal place of business") rather
  than a fixed named state — a genuinely defensible edge case either way.

## Raw run output: absent-clause set, n=73 (current/final)

```
$ python3 phase2.2_governing_law.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --absent --n 73 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 73 contracts with NO Governing Law clause (hallucination-rate check).

[ 1/73] (contract #1) OK  NELNETINC_04_08_2020-EX-1-JOINT FILING AGREEM...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1081 chars -> 1081 chars sent
        usage : in=1342 out=50 total=1392
[ 2/73] (contract #2) OK  PfHospitalityGroupInc_20150923_10-12G_EX-10.1...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 6772 chars -> 2839 chars sent
        usage : in=1730 out=50 total=1780
[ 3/73] (contract #3) OK  ThriventVariableInsuranceAccountB_20190701_N-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 4871 chars -> 4871 chars sent
        usage : in=2259 out=50 total=2309
[ 4/73] (contract #4) OK  Freecook_20180605_S-1_EX-10.3_11233807_EX-10....
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 6341 chars -> 6341 chars sent
        usage : in=2505 out=50 total=2555
[ 5/73] (contract #5) OK  GALACTICOMMTECHNOLOGIESINC_11_07_1997-EX-10.4...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1660 chars -> 1660 chars sent
        usage : in=1483 out=50 total=1533
[ 6/73] (contract #6) OK  PelicanDeliversInc_20200211_S-1_EX-10.3_11975...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16590 chars -> 16590 chars sent
        usage : in=4865 out=50 total=4915
[ 7/73] (contract #7) OK  ORBSATCORP_08_17_2007-EX-7.3-STRATEGIC ALLIAN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 18445 chars -> 13839 chars sent
        usage : in=4143 out=50 total=4193
[ 8/73] (contract #8) OK  GridironBionutrientsInc_20171206_8-K_EX-10.2_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3456 chars -> 3456 chars sent
        usage : in=2073 out=50 total=2123
[ 9/73] (contract #9) OK  VIRGINGALACTICHOLDINGS,INC_04_08_2020-EX-99.1...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1194 chars -> 1194 chars sent
        usage : in=1372 out=50 total=1422
[10/73] (contract #10) OK  TELEGLOBEINTERNATIONALHOLDINGSLTD_03_29_2004-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 94266 chars -> 70916 chars sent
        usage : in=17023 out=50 total=17073
[11/73] (contract #11) MISS NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO ...
        gold  : ''
        pred  : 'This Agreement, including its attachment and order acknowledgments under the Agreement, constitutes the entire agreement between Distributor and NETGEAR with respect to the purchase, resale and distribution of the Products and is governed by the laws of the State of California except that body of law dealing with conflicts of law.'
        pred matched patterns: ['governed by', 'laws of the state']
        src   : section-match
        ctx   : 8113 chars -> 630 chars sent
        usage : in=1209 out=113 total=1322
[12/73] (contract #12) OK  SECURIANFUNDSTRUST_05_01_2012-EX-99.28.H.9-NE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 9700 chars -> 9700 chars sent
        usage : in=3372 out=50 total=3422
[13/73] (contract #13) OK  BANGIINC_05_25_2005-EX-10-Premium Managed Hos...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2010 chars -> 2010 chars sent
        usage : in=1627 out=50 total=1677
[14/73] (contract #14) OK  PacificapEntertainmentHoldingsInc_20051115_8-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 18138 chars -> 7029 chars sent
        usage : in=2636 out=50 total=2686
[15/73] (contract #15) OK  RgcResourcesInc_20151216_8-K_EX-10.3_9372751_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5171 chars -> 5171 chars sent
        usage : in=2413 out=50 total=2463
[16/73] (contract #16) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2819 chars -> 2819 chars sent
        usage : in=1736 out=50 total=1786
[17/73] (contract #17) OK  XLITECHNOLOGIES,INC_12_11_2015-EX-10.1-Sponso...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 18240 chars -> 18240 chars sent
        usage : in=5261 out=50 total=5311
[18/73] (contract #18) OK  SLOVAKWIRELESSFINANCECOBV_03_28_2001-EX-4.(B)...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 33577 chars -> 33577 chars sent
        usage : in=7533 out=50 total=7583
[19/73] (contract #19) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1707 chars -> 1707 chars sent
        usage : in=1560 out=50 total=1610
[20/73] (contract #20) OK  ArcGroupInc_20171211_8-K_EX-10.1_10976103_EX-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16773 chars -> 16773 chars sent
        usage : in=4918 out=50 total=4968
[21/73] (contract #21) OK  VIVINT SOLAR, INC. - NON-COMPETITION AGREEMEN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3493 chars -> 2349 chars sent
        usage : in=1637 out=50 total=1687
[22/73] (contract #22) OK  FUSIONPHARMACEUTICALSINC_06_05_2020-EX-10.17-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 40597 chars -> 40583 chars sent
        usage : in=10299 out=50 total=10349
[23/73] (contract #23) OK  SalesforcecomInc_20171122_10-Q_EX-10.1_109615...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2935 chars -> 2935 chars sent
        usage : in=1825 out=50 total=1875
[24/73] (contract #24) OK  KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVIC...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 7600 chars -> 7600 chars sent
        usage : in=2935 out=50 total=2985
[25/73] (contract #25) OK  CardlyticsInc_20180112_S-1_EX-10.16_11002987_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5327 chars -> 5327 chars sent
        usage : in=2340 out=50 total=2390
[26/73] (contract #26) OK  XLITECHNOLOGIES,INC_12_02_2015-EX-10.02-STRAT...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5712 chars -> 5712 chars sent
        usage : in=2392 out=50 total=2442
[27/73] (contract #27) OK  BLACKROCKMUNIHOLDINGSINVESTMENTQUALITYFUND_04...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1283 chars -> 1283 chars sent
        usage : in=1385 out=50 total=1435
[28/73] (contract #28) OK  RMRGROUPINC_01_22_2020-EX-99.1-JOINT FILING A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 645 chars -> 645 chars sent
        usage : in=1278 out=50 total=1328
[29/73] (contract #29) OK  CHINARECYCLINGENERGYCORP_11_14_2013-EX-10.6-C...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 16509 chars -> 16509 chars sent
        usage : in=4560 out=50 total=4610
[30/73] (contract #30) OK  QBIOMEDINC_04_08_2020-EX-99.1-JOINT FILING AG...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2732 chars -> 2732 chars sent
        usage : in=1995 out=50 total=2045
[31/73] (contract #31) OK  BIOAMBERINC_04_10_2013-EX-10.34-DEVELOPMENT A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 6390 chars -> 6390 chars sent
        usage : in=2751 out=50 total=2801
[32/73] (contract #32) OK  IDREAMSKYTECHNOLOGYLTD_07_03_2014-EX-10.39-Co...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 76425 chars -> 76425 chars sent
        usage : in=17640 out=50 total=17690
[33/73] (contract #33) OK  ONEMAINHOLDINGS,INC_02_20_2020-EX-99.D-JOINT ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 5879 chars -> 5879 chars sent
        usage : in=2949 out=50 total=2999
[34/73] (contract #34) OK  NETGEAR,INC_04_21_2003-EX-10.16- AMENDMENT #2...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 4567 chars -> 4567 chars sent
        usage : in=2084 out=50 total=2134
[35/73] (contract #35) OK  SPRINGBANKPHARMACEUTICALS,INC_04_08_2020-EX-9...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1556 chars -> 1556 chars sent
        usage : in=1492 out=50 total=1542
[36/73] (contract #36) OK  SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3314 chars -> 741 chars sent
        usage : in=1249 out=50 total=1299
[37/73] (contract #37) OK  UNITEDNATIONALBANCORP_03_03_1999-EX-99-Outsou...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1952 chars -> 1952 chars sent
        usage : in=1555 out=50 total=1605
[38/73] (contract #38) OK  GALERATHERAPEUTICS,INC_02_14_2020-EX-99.A-JOI...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3892 chars -> 3892 chars sent
        usage : in=2260 out=50 total=2310
[39/73] (contract #39) OK  SOLUTIONSVENDINGINTERNATIONAL,INC_03_31_2020-...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 7124 chars -> 7124 chars sent
        usage : in=2684 out=50 total=2734
[40/73] (contract #40) OK  Cerus Corporation - FIRST AMEND TO SUPPLY AND...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11420 chars -> 11420 chars sent
        usage : in=3796 out=50 total=3846
[41/73] (contract #41) OK  OLDAPIWIND-DOWNLTD_01_08_2016-EX-1.3-AGENCY A...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3886 chars -> 3886 chars sent
        usage : in=2008 out=50 total=2058
[42/73] (contract #42) OK  ATENTOSA_07_06_2020-EX-99.1-JOINT FILING AGRE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2298 chars -> 2298 chars sent
        usage : in=1753 out=50 total=1803
[43/73] (contract #43) OK  RISEEDUCATIONCAYMANLTD_04_17_2020-EX-4.23-SER...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 16372 chars -> 16336 chars sent
        usage : in=4381 out=50 total=4431
[44/73] (contract #44) OK  SPIENERGYCO,LTD_07_10_2014-EX-10-Cooperation ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2811 chars -> 2811 chars sent
        usage : in=1696 out=50 total=1746
[45/73] (contract #45) OK  WatchitMediaInc_20061201_8-K_EX-10.1_4148672_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2106 chars -> 2106 chars sent
        usage : in=1573 out=50 total=1623
[46/73] (contract #46) OK  ADMA BioManufacturing, LLC -  Amendment #3 to...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 15312 chars -> 15312 chars sent
        usage : in=4928 out=50 total=4978
[47/73] (contract #47) MISS SoupmanInc_20150814_8-K_EX-10.1_9230148_EX-10...
        gold  : ''
        pred  : "This Guarantee shall be interpreted and construed under the laws of the state in which Franchisor has its principal place of business at the time the action is initiated. In the event of any conflict of law, the laws of such state shall prevail, without regard to the application of such state's conflict of law rules. If, however, any provision of this Guarantee would not be enforceable under the laws of the state in which Franchisor has its principal place of business at the time the action is initiated, and if the Master Franchisee's franchised business is located outside of such state and such provision would be enforceable under the laws of the state in which the Master Franchisee's franchised business is located, then such provision shall be interpreted and construed under the laws of that state."
        pred matched patterns: ['laws of the state']
        src   : section-match
        ctx   : 5504 chars -> 2079 chars sent
        usage : in=1560 out=222 total=1782
[48/73] (contract #48) OK  MANAKOASERVICESCORP_11_21_2007-EX-7.5-STRATEG...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 14879 chars -> 14864 chars sent
        usage : in=4402 out=50 total=4452
[49/73] (contract #49) OK  BizzingoInc_20120322_8-K_EX-10.17_7504499_EX-...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 24223 chars -> 3713 chars sent
        usage : in=1926 out=50 total=1976
[50/73] (contract #50) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 8024 chars -> 8024 chars sent
        usage : in=3015 out=50 total=3065
[51/73] (contract #51) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3422 chars -> 3422 chars sent
        usage : in=2048 out=50 total=2098
[52/73] (contract #52) OK  MFAFINANCIAL,INC_07_06_2020-EX-99.D-JOINT FIL...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3595 chars -> 3595 chars sent
        usage : in=2132 out=50 total=2182
[53/73] (contract #53) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11954 chars -> 11954 chars sent
        usage : in=4179 out=50 total=4229
[54/73] (contract #54) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2274 chars -> 2274 chars sent
        usage : in=1653 out=50 total=1703
[55/73] (contract #55) OK  UnionDentalHoldingsInc_20050204_8-KA_EX-10_33...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 14083 chars -> 12949 chars sent
        usage : in=4017 out=50 total=4067
[56/73] (contract #56) OK  WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-EN...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 7042 chars -> 2809 chars sent
        usage : in=1624 out=50 total=1674
[57/73] (contract #57) OK  PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3558 chars -> 3558 chars sent
        usage : in=1953 out=50 total=2003
[58/73] (contract #58) OK  ZtoExpressCaymanInc_20160930_F-1_EX-10.10_975...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 9174 chars -> 1255 chars sent
        usage : in=1369 out=50 total=1419
[59/73] (contract #59) OK  ScansourceInc_20190822_10-K_EX-10.39_11793959...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 10891 chars -> 2745 chars sent
        usage : in=1724 out=50 total=1774
[60/73] (contract #60) OK  PcquoteComInc_19990721_S-1A_EX-10.11_6377149_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 857 chars -> 857 chars sent
        usage : in=1352 out=50 total=1402
[61/73] (contract #61) OK  MACY_S,INC_05_11_2020-EX-99.4-JOINT FILING AG...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 1397 chars -> 1162 chars sent
        usage : in=1370 out=50 total=1420
[62/73] (contract #62) OK  PcquoteComInc_19990721_S-1A_EX-10.11_6377149_...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 2558 chars -> 2558 chars sent
        usage : in=1736 out=50 total=1786
[63/73] (contract #63) OK  GluMobileInc_20070319_S-1A_EX-10.09_436630_EX...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1902 chars -> 1902 chars sent
        usage : in=1580 out=50 total=1630
[64/73] (contract #64) OK  IMAGEWARESYSTEMSINC_12_20_1999-EX-10.22-MAINT...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 21778 chars -> 7981 chars sent
        usage : in=2796 out=50 total=2846
[65/73] (contract #65) OK  ZONDWINDSYSTEMPARTNERSLTDSERIES85-B_04_03_200...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 17712 chars -> 17712 chars sent
        usage : in=4004 out=50 total=4054
[66/73] (contract #66) OK  BellringBrandsInc_20190920_S-1_EX-10.12_11817...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 1742 chars -> 1742 chars sent
        usage : in=1508 out=50 total=1558
[67/73] (contract #67) OK  PRECIGEN,INC_01_22_2020-EX-99.1-JOINT FILING ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 972 chars -> 972 chars sent
        usage : in=1441 out=50 total=1491
[68/73] (contract #68) OK  PhotronicsInc_20171219_10-QA_EX-10.28_1098265...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 25392 chars -> 3949 chars sent
        usage : in=2059 out=50 total=2109
[69/73] (contract #69) OK  ALCOSTORESINC_12_14_2005-EX-10.26-AGENCY AGRE...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 11355 chars -> 11355 chars sent
        usage : in=3647 out=50 total=3697
[70/73] (contract #70) OK  NETZEEINC_11_14_2002-EX-10.3-MAINTENANCE AGRE...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 3474 chars -> 3446 chars sent
        usage : in=1849 out=50 total=1899
[71/73] (contract #71) OK  INGEVITYCORP_05_16_2016-EX-10.5-INTELLECTUAL ...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 63376 chars -> 5051 chars sent
        usage : in=2268 out=50 total=2318
[72/73] (contract #72) OK  NOVOINTEGRATEDSCIENCES,INC_12_23_2019-EX-10.1...
        gold  : ''
        pred  : ''
        src   : section-match
        ctx   : 21955 chars -> 5916 chars sent
        usage : in=2413 out=50 total=2463
[73/73] (contract #73) OK  TALLGRASSENERGY,LP_02_20_2020-EX-99.26-JOINT ...
        gold  : ''
        pred  : ''
        src   : full-contract fallback
        ctx   : 3971 chars -> 3971 chars sent
        usage : in=2198 out=50 total=2248

==================================================
HALLUCINATION RATE: 2/73 = 3%
CORRECTLY ABSTAINED: 71/73 = 97%
SECTION MATCHES: 22/73
FALLBACKS: 51/73
TOKENS: input=218328 output=3885 total=222213
AVG INPUT TOKENS / CONTRACT: 2990.8
AVG INPUT TOKENS / SECTION MATCH: 3349.3
AVG INPUT TOKENS / FALLBACK: 2836.2
CONTEXT CHARS: full=820125 snippets=610628
ESTIMATED COST: $0.7133
==================================================
```

## Raw run output: present-clause regression check, n=50 (same prompt, same code)

```
$ python3 phase2.2_governing_law.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --n 50 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 50 contracts that have a Governing Law clause.

[ 1/50] (contract #1) OK  LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGR...
        gold  : 'This Agreement is to be construed according to the laws          of the State of'
        pred  : 'This Agreement is to be construed according to the laws of the State of Illinois'
        src   : section-match
        ctx   : 54290 chars -> 6243 chars sent
        usage : in=2523 out=67 total=2590
[ 2/50] (contract #2) OK  WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION ...
        gold  : 'This Agreement is governed by English law and the parties submit to the exclusiv'
        pred  : 'This Agreement is governed by English law and the parties submit to the exclusiv'
        src   : section-match
        ctx   : 70383 chars -> 31973 chars sent
        usage : in=8139 out=112 total=8251
[ 3/50] (contract #3) OK  LohaCompanyltd_20191209_F-1_EX-10.16_11917878...
        gold  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        pred  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        src   : section-match
        ctx   : 11475 chars -> 1321 chars sent
        usage : in=1381 out=83 total=1464
[ 4/50] (contract #4) OK  CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-W...
        gold  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        pred  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        src   : section-match
        ctx   : 15176 chars -> 2586 chars sent
        usage : in=1613 out=100 total=1713
[ 5/50] (contract #5) OK  ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT ...
        gold  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        pred  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        src   : section-match
        ctx   : 24632 chars -> 112 chars sent
        usage : in=1106 out=68 total=1174
[ 6/50] (contract #6) OK  KIROMICBIOPHARMA,INC_05_11_2020-EX-10.23-CONS...
        gold  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        pred  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        src   : section-match
        ctx   : 18403 chars -> 17065 chars sent
        usage : in=4629 out=73 total=4702
[ 7/50] (contract #7) OK  VEONEER,INC_02_21_2020-EX-10.11-JOINT VENTURE...
        gold  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        pred  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 8257 chars -> 8211 chars sent
        usage : in=3428 out=67 total=3495
[ 8/50] (contract #8) OK  DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_...
        gold  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        pred  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        src   : section-match
        ctx   : 175580 chars -> 12116 chars sent
        usage : in=3869 out=118 total=3987
[ 9/50] (contract #9) OK  PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...
        gold  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        pred  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        src   : section-match
        ctx   : 145168 chars -> 119404 chars sent
        usage : in=28973 out=121 total=29094
[10/50] (contract #10) OK  MetLife, Inc. - Remarketing Agreement
        gold  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        pred  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        src   : section-match
        ctx   : 111249 chars -> 98213 chars sent
        usage : in=22489 out=126 total=22615
[11/50] (contract #11) OK  FTENETWORKS,INC_02_18_2016-EX-99.4-STRATEGIC ...
        gold  : 'The construction, interpretation, and performance of this Agreement and all tran'
        pred  : 'The construction, interpretation, and performance of this Agreement and all tran'
        src   : section-match
        ctx   : 37829 chars -> 5886 chars sent
        usage : in=2380 out=87 total=2467
[12/50] (contract #12) OK  DOMINIADVISORTRUST_02_18_2005-EX-99.(H)(2)-SP...
        gold  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        pred  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        src   : full-contract fallback
        ctx   : 12555 chars -> 12555 chars sent
        usage : in=3589 out=83 total=3672
[13/50] (contract #13) OK  CerenceInc_20191002_8-K_EX-10.4_11827494_EX-1...
        gold  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        pred  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        src   : section-match
        ctx   : 62170 chars -> 19318 chars sent
        usage : in=5527 out=111 total=5638
[14/50] (contract #14) OK  ReynoldsConsumerProductsInc_20191115_S-1_EX-1...
        gold  : 'This Agreement and all claims or causes of action arising out of or related to t'
        pred  : 'This Agreement and all claims or causes of action arising out of or related to t'
        src   : section-match
        ctx   : 61710 chars -> 60691 chars sent
        usage : in=13858 out=112 total=13970
[15/50] (contract #15) OK  IntegrityFunds_20200121_485BPOS_EX-99.E UNDR ...
        gold  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        pred  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        src   : section-match
        ctx   : 23845 chars -> 1239 chars sent
        usage : in=1354 out=67 total=1421
[16/50] (contract #16) OK  PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTEL...
        gold  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        pred  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        src   : section-match
        ctx   : 23282 chars -> 1681 chars sent
        usage : in=1414 out=103 total=1517
[17/50] (contract #17) OK  SIBANNAC,INC_12_04_2017-EX-2.1-Strategic Alli...
        gold  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        pred  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        src   : section-match
        ctx   : 8380 chars -> 2336 chars sent
        usage : in=1655 out=74 total=1729
[18/50] (contract #18) OK  INTRICONCORP_03_10_2009-EX-10.22-Strategic Al...
        gold  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        pred  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        src   : section-match
        ctx   : 52967 chars -> 26862 chars sent
        usage : in=7381 out=77 total=7458
[19/50] (contract #19) OK  BONTONSTORESINC_04_20_2018-EX-99.3-AGENCY AGR...
        gold  : 'This Agreement shall be governed by and interpreted in accordance with the laws '
        pred  : 'This Agreement shall be governed by and interpreted in accordance with the laws '
        src   : section-match
        ctx   : 161626 chars -> 111089 chars sent
        usage : in=26828 out=87 total=26915
[20/50] (contract #20) OK  ON2TECHNOLOGIES,INC_11_17_2006-EX-10.3-SUPPOR...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 61392 chars -> 39313 chars sent
        usage : in=9988 out=104 total=10092
[21/50] (contract #21) OK  OPERALTD_04_30_2020-EX-4.14-SERVICE AGREEMENT
        gold  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        pred  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        src   : section-match
        ctx   : 20983 chars -> 2987 chars sent
        usage : in=1741 out=92 total=1833
[22/50] (contract #22) MISS BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT V...
        gold  : 'By this Agreement the Members enter into a joint venture (the "Venture") in accordance with the laws of the State of Florida.'
        pred  : ''
        pred matched patterns: NONE
        src   : section-match
        ctx   : 21450 chars -> 4646 chars sent
        usage : in=2061 out=50 total=2111
[23/50] (contract #23) OK  ZEBRATECHNOLOGIESCORP_04_16_2014-EX-10.1-INTE...
        gold  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        pred  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        src   : section-match
        ctx   : 127205 chars -> 40538 chars sent
        usage : in=10239 out=104 total=10343
[24/50] (contract #24) OK  ChinaRealEstateInformationCorp_20090929_F-1_E...
        gold  : 'This Termination Agreement shall be governed by the laws of the PRC, without reg'
        pred  : 'This Agreement and any dispute or claim arising out of or in connection with it '
        src   : section-match
        ctx   : 49191 chars -> 15454 chars sent
        usage : in=4728 out=114 total=4842
[25/50] (contract #25) OK  HERTZGLOBALHOLDINGS,INC_07_07_2016-EX-10.4-IN...
        gold  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        pred  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        src   : section-match
        ctx   : 30968 chars -> 30554 chars sent
        usage : in=8623 out=121 total=8744
[26/50] (contract #26) OK  GLOBALTECHNOLOGIESLTD_06_08_2020-EX-10.16-CON...
        gold  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        pred  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        src   : section-match
        ctx   : 20805 chars -> 4084 chars sent
        usage : in=1901 out=89 total=1990
[27/50] (contract #27) OK  PfHospitalityGroupInc_20150923_10-12G_EX-10.1...
        gold  : 'This Agreement and the relationship between the parties is governed by and will '
        pred  : 'This Agreement and the relationship between the parties is governed by and will '
        src   : section-match
        ctx   : 152649 chars -> 5010 chars sent
        usage : in=2364 out=95 total=2459
[28/50] (contract #28) OK  CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTI...
        gold  : 'This Agreement shall be governed by         the laws of the State of California,'
        pred  : 'This Agreement shall be governed by the laws of the State of California, USA, ex'
        src   : section-match
        ctx   : 62324 chars -> 52814 chars sent
        usage : in=11989 out=92 total=12081
[29/50] (contract #29) OK  TUNIUCORP_03_06_2014-EX-10-COOPERATION AGREEM...
        gold  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        pred  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        src   : section-match
        ctx   : 17917 chars -> 17903 chars sent
        usage : in=4910 out=118 total=5028
[30/50] (contract #30) OK  CYBERIANOUTPOSTINC_07_09_1998-EX-10.13-PROMOT...
        gold  : 'This Agreement will be construed in accordance with           and governed by th'
        pred  : 'This Agreement will be construed in accordance with and governed by the laws of '
        src   : section-match
        ctx   : 25288 chars -> 23373 chars sent
        usage : in=6036 out=80 total=6116
[31/50] (contract #31) OK  SENMIAOTECHNOLOGYLTD_02_19_2019-EX-10.5-Colla...
        gold  : 'The execution, validation, interpretation, performance, modification and termina'
        pred  : 'The execution, validation, interpretation, performance, modification and termina'
        src   : section-match
        ctx   : 73890 chars -> 1412 chars sent
        usage : in=1375 out=83 total=1458
[32/50] (contract #32) OK  HealthcareIntegratedTechnologiesInc_20190812_...
        gold  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        pred  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        src   : section-match
        ctx   : 22288 chars -> 2854 chars sent
        usage : in=1625 out=136 total=1761
[33/50] (contract #33) OK  LOYALTYPOINTINC_11_16_2004-EX-10.2-RESELLER A...
        gold  : 'This Agreement shall be subject to and governed by the laws of the          Stat'
        pred  : 'This Agreement shall be deemed to have been made and executed in the State of Mi'
        src   : section-match
        ctx   : 117478 chars -> 23340 chars sent
        usage : in=5665 out=96 total=5761
[34/50] (contract #34) OK  BNCMORTGAGEINC_05_17_1999-EX-10.4-LICENSING A...
        gold  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        pred  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        src   : section-match
        ctx   : 32680 chars -> 19062 chars sent
        usage : in=5002 out=81 total=5083
[35/50] (contract #35) OK  ENERGOUSCORP_03_16_2017-EX-10.24-STRATEGIC AL...
        gold  : 'This Letter of Authorization will be governed by and construed in accordance wit'
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 81926 chars -> 9809 chars sent
        usage : in=3236 out=77 total=3313
[36/50] (contract #36) OK  CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-...
        gold  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        pred  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        src   : section-match
        ctx   : 159488 chars -> 10552 chars sent
        usage : in=3449 out=110 total=3559
[37/50] (contract #37) OK  MSCIINC_02_28_2008-EX-10.10-
        gold  : 'This Agreement shall be construed in accordance with and governed by the substan'
        pred  : 'This Agreement shall be construed in accordance with and governed by the substan'
        src   : section-match
        ctx   : 11770 chars -> 9056 chars sent
        usage : in=3197 out=74 total=3271
[38/50] (contract #38) OK  NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEME...
        gold  : 'This Agreement shall be governed by and           construed in accordance with t'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 148163 chars -> 41924 chars sent
        usage : in=9730 out=79 total=9809
[39/50] (contract #39) OK  ImpresseCorp_20000322_S-1A_EX-10.11_5199234_E...
        gold  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        pred  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        src   : section-match
        ctx   : 47639 chars -> 16827 chars sent
        usage : in=4911 out=75 total=4986
[40/50] (contract #40) OK  AlliedEsportsEntertainmentInc_20190815_8-K_EX...
        gold  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        pred  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        src   : section-match
        ctx   : 35504 chars -> 6728 chars sent
        usage : in=2675 out=92 total=2767
[41/50] (contract #41) OK  CHERRYHILLMORTGAGEINVESTMENTCORP_09_26_2013-E...
        gold  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        pred  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        src   : section-match
        ctx   : 27741 chars -> 27624 chars sent
        usage : in=7065 out=94 total=7159
[42/50] (contract #42) OK  CreditcardscomInc_20070810_S-1_EX-10.33_36229...
        gold  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        pred  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        src   : section-match
        ctx   : 28804 chars -> 1531 chars sent
        usage : in=1528 out=75 total=1603
[43/50] (contract #43) OK  Zounds Hearing, Inc. - MANUFACTURING DESIGN M...
        gold  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        pred  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        src   : section-match
        ctx   : 47001 chars -> 3198 chars sent
        usage : in=1748 out=88 total=1836
[44/50] (contract #44) OK  CUROGROUPHOLDINGSCORP_05_04_2020-EX-10.3-SERV...
        gold  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        pred  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        src   : section-match
        ctx   : 36602 chars -> 34031 chars sent
        usage : in=8710 out=143 total=8853
[45/50] (contract #45) OK  SouthernStarEnergyInc_20051202_SB-2A_EX-9_801...
        gold  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        pred  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        src   : section-match
        ctx   : 22721 chars -> 1859 chars sent
        usage : in=1517 out=79 total=1596
[46/50] (contract #46) OK  ConformisInc_20191101_10-Q_EX-10.6_11861402_E...
        gold  : 'This Agreement shall be governed and construed in accordance with the laws of Ne'
        pred  : 'This Agreement shall be governed and construed in accordance with the laws of Ne'
        src   : section-match
        ctx   : 63217 chars -> 8801 chars sent
        usage : in=3098 out=80 total=3178
[47/50] (contract #47) OK  Principal Life Insurance Company - Broker Dea...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 29599 chars -> 9458 chars sent
        usage : in=3156 out=70 total=3226
[48/50] (contract #48) OK  LegacyEducationAllianceInc_20200330_10-K_EX-1...
        gold  : 'This Agreement will be governed by and construed in accordance with the laws of '
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 46255 chars -> 9188 chars sent
        usage : in=3275 out=102 total=3377
[49/50] (contract #49) OK  VerizonAbsLlc_20200123_8-K_EX-10.4_11952335_E...
        gold  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        pred  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        src   : section-match
        ctx   : 289615 chars -> 63749 chars sent
        usage : in=16013 out=269 total=16282
[50/50] (contract #50) OK  VERICELCORP_08_06_2019-EX-10.10-SUPPLY AGREEM...
        gold  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        pred  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        src   : section-match
        ctx   : 102006 chars -> 10220 chars sent
        usage : in=3400 out=94 total=3494

==================================================
ACCURACY: 49/50 = 98%
SECTION MATCHES: 49/50
FALLBACKS: 1/50
TOKENS: input=297091 output=4792 total=301883
AVG INPUT TOKENS / CONTRACT: 5941.8
AVG INPUT TOKENS / SECTION MATCH: 5989.8
AVG INPUT TOKENS / FALLBACK: 3589.0
CONTEXT CHARS: full=3093536 snippets=1086800
ESTIMATED COST: $0.9632
==================================================
```
