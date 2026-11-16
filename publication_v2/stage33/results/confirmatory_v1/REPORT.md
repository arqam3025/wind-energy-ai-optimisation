# Stage 3.3 confirmatory results

Study role: SYNTHETIC_CONFIRMATORY_HELD_OUT_SEEDS  
Protocol SHA-256: `bed65ff8d1c82b282068237071338599d33e80bb6d8e02addb4a832177c72cec`  
Code commit: `c59a2c15f3692f12773e68d30eadaa05cfdbbef5`  
Runs: 18900

## Primary hypotheses (Holm-adjusted, one-sided, alpha 0.05)

| Test | Forecast | n | Margin | Mean diff [95% CI] | Median | p | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|---|
| H1 | oracle25 | 150 | 0.0 | -1470.5 [-1720.7, -1240.8] | -1064.1 | 1.08e-24 | 6.47e-24 | yes |
| H2a | oracle25 | 150 | 0.0 | -286.1 [-311.4, -261.3] | -277.0 | 1.68e-26 | 1.51e-25 | yes |
| H2b | oracle25 | 150 | 148.4 | +8.1 [-0.7, +14.4] | +3.9 | 6.49e-27 | 6.49e-26 | yes |
| H1 | oracle50 | 150 | 0.0 | -1450.6 [-1699.1, -1221.9] | -1060.9 | 1.57e-24 | 7.87e-24 | yes |
| H2a | oracle50 | 150 | 0.0 | -561.1 [-592.2, -529.2] | -572.4 | 2.41e-26 | 1.93e-25 | yes |
| H2b | oracle50 | 150 | 148.4 | +23.0 [+15.1, +32.4] | +9.9 | 2.80e-25 | 1.96e-24 | yes |
| H1 | oracle100 | 150 | 0.0 | -1286.1 [-1530.9, -1061.3] | -821.5 | 2.56e-23 | 1.02e-22 | yes |
| H2a | oracle100 | 150 | 0.0 | -393.0 [-458.2, -329.8] | -356.5 | 1.45e-20 | 4.35e-20 | yes |
| H2b | oracle100 | 150 | 148.4 | +44.3 [+19.8, +69.6] | +23.5 | 2.04e-14 | 4.08e-14 | yes |
| H3 | persistence | 150 | 74.2 | +0.0 [+0.0, +0.0] | +0.0 | 8.67e-35 | 1.13e-33 | yes |
| H3 | mean_reversion | 150 | 74.2 | +37.8 [+17.6, +59.5] | +0.0 | 1.04e-10 | 1.04e-10 | yes |
| H3 | skill_combo | 150 | 74.2 | +4.2 [-0.2, +11.6] | +0.0 | 6.45e-32 | 7.10e-31 | yes |
| H3 | damped_trend | 150 | 74.2 | +0.6 [+0.0, +1.8] | +0.0 | 1.45e-34 | 1.74e-33 | yes |

## Secondary: H2b at the originally drafted 5% margin (unadjusted; see protocol Section 5)

| Forecast | Margin | Mean diff | p (one-sided, unadjusted) |
|---|---|---|---|
| oracle25 | 74.2 | +8.1 | 2.24e-25 |
| oracle50 | 74.2 | +23.0 | 1.97e-21 |
| oracle100 | 74.2 | +44.3 | 3.49e-05 |

## Secondary (descriptive, pooled over volatility)

```

## oracle25  (n=150, MAE30=35 kW, marginal cov=0.91, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic             10631   675     45137
fixed_margin               1043    71    233248
adaptive                    786    26     98089
heuristic                 17005   873     50524
stochastic                 1848   152     55214
stochastic_no_gate         1444   132     55743
stochastic_terminal        1365   139     61321
point_band_gate           12296   743     40962
stochastic_increments       1572   141     55092
stochastic_skill           2007   154     55181
stochastic_skill00         2007   154     55181
stochastic_skill05         2007   154     55181
stochastic_skill20         2007   154     55181
  stochastic-uncontrolled          d_exceed -1472 [-1721,-1242] p=0.000        d_thru +368 [+320,+418] p=0.000
  stochastic-adaptive              d_exceed +7 [-2,+13] p=0.000                d_thru -286 [-311,-261] p=0.000
  stochastic-fixed_margin          d_exceed +5 [+2,+9] p=0.000                 d_thru -1187 [-1235,-1137] p=0.000
  stochastic-deterministic         d_exceed -59 [-68,-50] p=0.000              d_thru +67 [+59,+76] p=0.000
  stochastic-stochastic_no_gate    d_exceed +3 [+2,+4] p=0.000                 d_thru -4 [-4,-3] p=0.000
  stochastic-stochastic_terminal   d_exceed +3 [+1,+6] p=0.004                 d_thru -41 [-55,-28] p=0.000
  stochastic-point_band_gate       d_exceed -70 [-79,-61] p=0.000              d_thru +95 [+84,+106] p=0.000
  stochastic_increments-uncontrolled d_exceed -1473 [-1724,-1243] p=0.000        d_thru +367 [+319,+416] p=0.000
  stochastic_increments-stochastic d_exceed -2 [-4,-0] p=0.029                 d_thru -1 [-4,+2] p=0.887
  stochastic_increments-adaptive   d_exceed +5 [-3,+11] p=0.000                d_thru -287 [-312,-262] p=0.000
  stochastic_increments-deterministic d_exceed -60 [-69,-52] p=0.000              d_thru +66 [+58,+75] p=0.000

## oracle50  (n=150, MAE30=69 kW, marginal cov=0.91, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic             20540   720     53401
fixed_margin               3432   131    237183
adaptive                   1549    67    169914
heuristic                 30029   889     53851
stochastic                 4339   191     86146
stochastic_no_gate         3976   181     87389
stochastic_terminal        4708   205    103005
point_band_gate           22461   761     46012
stochastic_increments       3241   157     84959
stochastic_skill           4996   198     85757
stochastic_skill00         4839   196     85830
stochastic_skill05         4841   197     85804
stochastic_skill20         4997   199     85745
  stochastic-uncontrolled          d_exceed -1455 [-1704,-1227] p=0.000        d_thru +574 [+511,+641] p=0.000
  stochastic-adaptive              d_exceed +19 [+13,+25] p=0.000              d_thru -558 [-589,-526] p=0.000
  stochastic-fixed_margin          d_exceed +6 [-1,+13] p=0.024                d_thru -1007 [-1052,-960] p=0.000
  stochastic-deterministic         d_exceed -108 [-124,-93] p=0.000            d_thru +218 [+193,+245] p=0.000
  stochastic-stochastic_no_gate    d_exceed +2 [+1,+4] p=0.000                 d_thru -8 [-12,-6] p=0.000
  stochastic-stochastic_terminal   d_exceed -2 [-7,+2] p=0.304                 d_thru -112 [-138,-88] p=0.000
  stochastic-point_band_gate       d_exceed -121 [-138,-105] p=0.000           d_thru +268 [+238,+298] p=0.000
  stochastic_increments-uncontrolled d_exceed -1462 [-1711,-1233] p=0.000        d_thru +566 [+504,+631] p=0.000
  stochastic_increments-stochastic d_exceed -7 [-11,-4] p=0.000                d_thru -8 [-14,-2] p=0.216
  stochastic_increments-adaptive   d_exceed +11 [+7,+16] p=0.000               d_thru -566 [-595,-536] p=0.000
  stochastic_increments-deterministic d_exceed -115 [-131,-100] p=0.000           d_thru +210 [+188,+234] p=0.000

## oracle100  (n=150, MAE30=137 kW, marginal cov=0.91, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic             47236   876     79240
fixed_margin              24665   493    251350
adaptive                  23018   490    238381
heuristic                 56293   941     66175
stochastic                26533   527    194249
stochastic_no_gate        26019   522    196841
stochastic_terminal       28842   619    232679
point_band_gate           42737   812     63106
stochastic_increments      20605   436    193024
stochastic_skill          29669   554    179426
stochastic_skill00        29783   549    180617
stochastic_skill05        29924   549    180145
stochastic_skill20        30799   559    176683
  stochastic-uncontrolled          d_exceed -1307 [-1548,-1083] p=0.000        d_thru +1295 [+1205,+1387] p=0.000
  stochastic-adaptive              d_exceed +23 [+3,+44] p=0.030               d_thru -294 [-340,-248] p=0.000
  stochastic-fixed_margin          d_exceed +12 [-10,+35] p=0.515              d_thru -381 [-436,-327] p=0.000
  stochastic-deterministic         d_exceed -138 [-167,-109] p=0.000           d_thru +767 [+710,+824] p=0.000
  stochastic-stochastic_no_gate    d_exceed +3 [-1,+9] p=0.097                 d_thru -17 [-24,-11] p=0.000
  stochastic-stochastic_terminal   d_exceed -15 [-30,-1] p=0.002               d_thru -256 [-289,-223] p=0.000
  stochastic-point_band_gate       d_exceed -108 [-141,-76] p=0.000            d_thru +874 [+816,+936] p=0.000
  stochastic_increments-uncontrolled d_exceed -1347 [-1591,-1121] p=0.000        d_thru +1287 [+1204,+1371] p=0.000
  stochastic_increments-stochastic d_exceed -40 [-59,-20] p=0.000              d_thru -8 [-27,+10] p=0.694
  stochastic_increments-adaptive   d_exceed -16 [-34,+4] p=0.008               d_thru -302 [-342,-262] p=0.000
  stochastic_increments-deterministic d_exceed -178 [-209,-145] p=0.000           d_thru +759 [+710,+809] p=0.000

## oracle150  (n=150, MAE30=201 kW, marginal cov=0.91, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic             90926  1168    115553
fixed_margin              95836  1305    273741
adaptive                  94288  1272    273537
heuristic                 87886  1101     88630
stochastic               103186  1351    287600
stochastic_no_gate       103362  1354    289589
stochastic_terminal      108932  1401    311309
point_band_gate           73874  1024     91945
stochastic_increments      92194  1286    278115
stochastic_skill         104750  1273    196676
stochastic_skill00       100915  1272    210777
stochastic_skill05       101259  1262    203875
stochastic_skill20       110085  1265    176071
  stochastic-uncontrolled          d_exceed -796 [-1038,-574] p=0.000          d_thru +1917 [+1832,+2002] p=0.000
  stochastic-adaptive              d_exceed +59 [+25,+94] p=0.002              d_thru +94 [+52,+137] p=0.000
  stochastic-fixed_margin          d_exceed +49 [+15,+84] p=0.019              d_thru +92 [+47,+139] p=0.000
  stochastic-deterministic         d_exceed +82 [+29,+134] p=0.005             d_thru +1147 [+1082,+1214] p=0.000
  stochastic-stochastic_no_gate    d_exceed -1 [-11,+9] p=0.747                d_thru -13 [-20,-7] p=0.000
  stochastic-stochastic_terminal   d_exceed -38 [-61,-16] p=0.001              d_thru -158 [-187,-129] p=0.000
  stochastic-point_band_gate       d_exceed +195 [+144,+246] p=0.000           d_thru +1304 [+1240,+1370] p=0.000
  stochastic_increments-uncontrolled d_exceed -869 [-1109,-644] p=0.000          d_thru +1854 [+1777,+1931] p=0.000
  stochastic_increments-stochastic d_exceed -73 [-99,-47] p=0.000              d_thru -63 [-88,-39] p=0.000
  stochastic_increments-adaptive   d_exceed -14 [-39,+12] p=0.147              d_thru +31 [-3,+65] p=0.066
  stochastic_increments-deterministic d_exceed +8 [-40,+57] p=0.586               d_thru +1084 [+1027,+1143] p=0.000

## oracle200  (n=150, MAE30=263 kW, marginal cov=0.91, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic            178742  1755    166938
fixed_margin             215593  2088    301789
adaptive                 205761  2006    296913
heuristic                146726  1454    119548
stochastic               186261  1847    276497
stochastic_no_gate       186883  1857    277080
stochastic_terminal      211423  1951    313507
point_band_gate          137279  1491    130805
stochastic_increments     184452  1863    278592
stochastic_skill         167195  1552    106082
stochastic_skill00       163678  1541    122853
stochastic_skill05       170029  1553    115013
stochastic_skill20       172434  1529     88997
  stochastic-uncontrolled          d_exceed -242 [-474,-27] p=0.812            d_thru +1843 [+1773,+1913] p=0.000
  stochastic-adaptive              d_exceed -130 [-175,-84] p=0.000            d_thru -136 [-179,-94] p=0.000
  stochastic-fixed_margin          d_exceed -196 [-243,-149] p=0.000           d_thru -169 [-212,-126] p=0.000
  stochastic-deterministic         d_exceed +50 [-17,+116] p=0.063             d_thru +730 [+677,+785] p=0.000
  stochastic-stochastic_no_gate    d_exceed -4 [-8,-1] p=0.105                 d_thru -4 [-7,-1] p=0.001
  stochastic-stochastic_terminal   d_exceed -168 [-201,-135] p=0.000           d_thru -247 [-282,-213] p=0.000
  stochastic-point_band_gate       d_exceed +327 [+268,+384] p=0.000           d_thru +971 [+921,+1025] p=0.000
  stochastic_increments-uncontrolled d_exceed -254 [-489,-36] p=0.975            d_thru +1857 [+1790,+1924] p=0.000
  stochastic_increments-stochastic d_exceed -12 [-41,+18] p=0.249              d_thru +14 [-6,+35] p=0.253
  stochastic_increments-adaptive   d_exceed -142 [-184,-100] p=0.000           d_thru -122 [-160,-85] p=0.000
  stochastic_increments-deterministic d_exceed +38 [-31,+106] p=0.158             d_thru +744 [+694,+796] p=0.000

## persistence  (n=150, MAE30=215 kW, marginal cov=0.90, joint=0.74)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic            222587  1581         0
fixed_margin             222587  1581         0
adaptive                 223304  1594     35118
heuristic                222587  1581         0
stochastic               224636  1594     13201
stochastic_no_gate       225337  1598     18917
stochastic_terminal      225867  1609     20650
point_band_gate          222587  1581         0
stochastic_increments     225560  1582     26849
stochastic_skill         222587  1581         0
stochastic_skill00       222587  1581         0
stochastic_skill05       222587  1581         0
stochastic_skill20       222587  1581         0
  stochastic-uncontrolled          d_exceed +14 [+7,+22] p=0.001               d_thru +88 [+60,+118] p=0.000
  stochastic-adaptive              d_exceed +9 [-1,+19] p=0.340                d_thru -146 [-184,-109] p=0.000
  stochastic-fixed_margin          d_exceed +14 [+7,+22] p=0.001               d_thru +88 [+60,+118] p=0.000
  stochastic-deterministic         d_exceed +14 [+7,+22] p=0.001               d_thru +88 [+60,+118] p=0.000
  stochastic-stochastic_no_gate    d_exceed -5 [-11,+0] p=0.278                d_thru -38 [-54,-24] p=0.000
  stochastic-stochastic_terminal   d_exceed -8 [-16,-2] p=0.015                d_thru -50 [-75,-28] p=0.000
  stochastic-point_band_gate       d_exceed +14 [+7,+22] p=0.001               d_thru +88 [+60,+118] p=0.000
  stochastic_increments-uncontrolled d_exceed +20 [+11,+30] p=0.000              d_thru +179 [+137,+225] p=0.000
  stochastic_increments-stochastic d_exceed +6 [-5,+18] p=0.333                d_thru +91 [+64,+120] p=0.000
  stochastic_increments-adaptive   d_exceed +15 [+5,+26] p=0.096               d_thru -55 [-95,-14] p=0.001
  stochastic_increments-deterministic d_exceed +20 [+11,+30] p=0.000              d_thru +179 [+137,+225] p=0.000

## mean_reversion  (n=150, MAE30=237 kW, marginal cov=0.90, joint=0.76)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic            231207  1600     15452
fixed_margin             250242  1689    179908
adaptive                 251742  1717    169362
heuristic                227371  1580     10124
stochastic               245939  1687    105326
stochastic_no_gate       246773  1681    128237
stochastic_terminal      252208  1728    149552
point_band_gate          226335  1579      9893
stochastic_increments     242874  1671    113844
stochastic_skill         228257  1614     15606
stochastic_skill00       233519  1634     35828
stochastic_skill05       232180  1628     25229
stochastic_skill20       226450  1599      5650
  stochastic-uncontrolled          d_exceed +156 [+112,+202] p=0.000           d_thru +702 [+613,+794] p=0.000
  stochastic-adaptive              d_exceed -39 [-74,-1] p=0.002               d_thru -427 [-500,-351] p=0.000
  stochastic-fixed_margin          d_exceed -29 [-65,+10] p=0.005              d_thru -497 [-567,-425] p=0.000
  stochastic-deterministic         d_exceed +98 [+61,+137] p=0.000             d_thru +599 [+525,+676] p=0.000
  stochastic-stochastic_no_gate    d_exceed -6 [-20,+9] p=0.465                d_thru -153 [-184,-124] p=0.000
  stochastic-stochastic_terminal   d_exceed -42 [-65,-19] p=0.000              d_thru -295 [-351,-242] p=0.000
  stochastic-point_band_gate       d_exceed +131 [+90,+173] p=0.000            d_thru +636 [+560,+715] p=0.000
  stochastic_increments-uncontrolled d_exceed +135 [+96,+175] p=0.000            d_thru +759 [+675,+845] p=0.000
  stochastic_increments-stochastic d_exceed -20 [-39,-3] p=0.108               d_thru +57 [+26,+88] p=0.000
  stochastic_increments-adaptive   d_exceed -59 [-88,-29] p=0.000              d_thru -370 [-440,-299] p=0.000
  stochastic_increments-deterministic d_exceed +78 [+47,+110] p=0.000             d_thru +656 [+586,+729] p=0.000

## skill_combo  (n=150, MAE30=221 kW, marginal cov=0.90, joint=0.75)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic            222527  1580        18
fixed_margin             233645  1592    119621
adaptive                 234705  1641    114063
heuristic                222587  1581         0
stochastic               229885  1610     35943
stochastic_no_gate       230083  1635     52398
stochastic_terminal      231937  1620     49651
point_band_gate          222587  1581         4
stochastic_increments     231682  1610     48502
stochastic_skill         223224  1584       627
stochastic_skill00       226616  1602     13956
stochastic_skill05       224584  1590      5814
stochastic_skill20       222587  1581         0
  stochastic-uncontrolled          d_exceed +49 [+29,+71] p=0.000              d_thru +240 [+187,+296] p=0.000
  stochastic-adaptive              d_exceed -32 [-53,-13] p=0.001              d_thru -521 [-584,-458] p=0.000
  stochastic-fixed_margin          d_exceed -25 [-47,-3] p=0.013               d_thru -558 [-610,-505] p=0.000
  stochastic-deterministic         d_exceed +49 [+29,+71] p=0.000              d_thru +239 [+187,+296] p=0.000
  stochastic-stochastic_no_gate    d_exceed -1 [-11,+8] p=0.942                d_thru -110 [-134,-87] p=0.000
  stochastic-stochastic_terminal   d_exceed -14 [-28,-1] p=0.020               d_thru -91 [-120,-66] p=0.000
  stochastic-point_band_gate       d_exceed +49 [+29,+71] p=0.000              d_thru +240 [+187,+296] p=0.000
  stochastic_increments-uncontrolled d_exceed +61 [+37,+86] p=0.000              d_thru +323 [+265,+384] p=0.000
  stochastic_increments-stochastic d_exceed +12 [-4,+28] p=0.100               d_thru +84 [+58,+110] p=0.000
  stochastic_increments-adaptive   d_exceed -20 [-42,+2] p=0.020               d_thru -437 [-501,-371] p=0.000
  stochastic_increments-deterministic d_exceed +61 [+37,+86] p=0.000              d_thru +323 [+265,+384] p=0.000

## damped_trend  (n=150, MAE30=297 kW, marginal cov=0.90, joint=0.78)
controller            exceed kW  viol  thru kWh
uncontrolled             222587  1581         0
deterministic            260725  1668     24276
fixed_margin             308680  1910    169122
adaptive                 304953  1870    169508
heuristic                253540  1641     16018
stochastic               307028  1823    121156
stochastic_no_gate       308090  1832    129178
stochastic_terminal      315462  1880    151880
point_band_gate          252382  1638     15972
stochastic_increments     307981  1860    131552
stochastic_skill         222678  1582       415
stochastic_skill00       223510  1588      2222
stochastic_skill05       222777  1584      1183
stochastic_skill20       222587  1581         0
  stochastic-uncontrolled          d_exceed +563 [+460,+674] p=0.000           d_thru +808 [+726,+895] p=0.000
  stochastic-adaptive              d_exceed +14 [-35,+62] p=0.913              d_thru -322 [-385,-259] p=0.000
  stochastic-fixed_margin          d_exceed -11 [-58,+38] p=0.315              d_thru -320 [-379,-260] p=0.000
  stochastic-deterministic         d_exceed +309 [+246,+374] p=0.000           d_thru +646 [+581,+715] p=0.000
  stochastic-stochastic_no_gate    d_exceed -7 [-20,+5] p=0.143                d_thru -53 [-65,-42] p=0.000
  stochastic-stochastic_terminal   d_exceed -56 [-82,-33] p=0.000              d_thru -205 [-236,-173] p=0.000
  stochastic-point_band_gate       d_exceed +364 [+302,+430] p=0.000           d_thru +701 [+631,+776] p=0.000
  stochastic_increments-uncontrolled d_exceed +569 [+466,+681] p=0.000           d_thru +877 [+801,+957] p=0.000
  stochastic_increments-stochastic d_exceed +6 [-18,+30] p=0.207               d_thru +69 [+38,+102] p=0.000
  stochastic_increments-adaptive   d_exceed +20 [-29,+71] p=0.649              d_thru -253 [-318,-187] p=0.000
  stochastic_increments-deterministic d_exceed +315 [+256,+377] p=0.000           d_thru +715 [+653,+780] p=0.000
```