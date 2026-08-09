# Final V2 Assembled Golden Records

## Problem: 1008B

```json
{
  "problem_id": "1008B",
  "problem_url": "https://codeforces.com/problemset/problem/1008/B",
  "problem_metadata": {
    "name": "Turn the Rectangles",
    "tags": [
      "greedy",
      "sortings"
    ],
    "time_limit_ms": 2000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">B. Turn the Rectangles</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>2 seconds</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\"><div class=\"property-title\">input</div>standard input</div><div class=\"output-file output-standard\"><div class=\"property-title\">output</div>standard output</div></div><div><p>There are $$$n$$$ rectangles in a row. You can either turn each rectangle by $$$90$$$ degrees or leave it as it is. If you turn a rectangle, its width will be height, and its height will be width. Notice that you can turn any number of rectangles, you also can turn all or none of them. <span class=\"tex-font-style-bf\">You can not change the order of the rectangles.</span></p><p>Find out if there is a way to make the rectangles go in order of non-ascending height. In other words, after all the turns, a height of every rectangle has to be not greater than the height of the previous rectangle (if it is such). </p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line contains a single integer $$$n$$$ ($$$1 \\leq n \\leq 10^5$$$)\u00a0\u2014 the number of rectangles.</p><p>Each of the next $$$n$$$ lines contains two integers $$$w_i$$$ and $$$h_i$$$ ($$$1 \\leq w_i, h_i \\leq 10^9$$$)\u00a0\u2014 the width and the height of the $$$i$$$-th rectangle.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>Print \"<span class=\"tex-font-style-tt\">YES</span>\" (without quotes) if there is a way to make the rectangles go in order of non-ascending height, otherwise print \"<span class=\"tex-font-style-tt\">NO</span>\".</p><p>You can print each letter in any case (upper or lower).</p></div><div class=\"sample-tests\"><div class=\"section-title\">Examples</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>3<br/>3 4<br/>4 6<br/>3 5<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>YES<br/></pre></div><div class=\"input\"><div class=\"title\">Input</div><pre>2<br/>3 4<br/>5 5<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>NO<br/></pre></div></div></div><div class=\"note\"><div class=\"section-title\">Note</div><p>In the first test, you can rotate the second and the third rectangles so that the heights will be <span class=\"tex-font-style-tt\">[4, 4, 3]</span>.</p><p>In the second test, there is no way the second rectangle will be not higher than the first one.</p></div></div>",
  "pretests": [
    {
      "input": "3\r\n3 4\r\n4 6\r\n3 5",
      "output": "YES"
    },
    {
      "input": "2\r\n3 4\r\n5 5",
      "output": "NO"
    },
    {
      "input": "10\r\n4 3\r\n1 1\r\n6 5\r\n4 5\r\n2 4\r\n9 5\r\n7 9\r\n9 2\r\n4 10\r\n10 1",
      "output": "NO"
    },
    {
      "input": "10\r\n241724251 76314740\r\n80658193 177743680\r\n213953908 406274173\r\n485639518 859188055\r\n103578427 56645210\r\n611931853 374099541\r\n916667853 408945969\r\n677773241 808703176\r\n575586508 440395988\r\n450102404 244301685",
      "output": "NO"
    },
    {
      "input": "10\r\n706794178 103578427\r\n431808055 641644550\r\n715688799 406274173\r\n767234853 345348548\r\n241724251 408945969\r\n808703176 213953908\r\n185314264 16672343\r\n553496707 152702033\r\n105991807 76314740\r\n61409204 244301685",
      "output": "YES"
    },
    {
      "input": "100000\r\n76827 7782\r\n4937 12393\r\n79440 52681\r\n73202 19594\r\n77062 40773\r\n76173 7230\r\n5533 97078\r\n59529 89716\r\n96221 53954\r\n32349 51550\r\n51030 73580\r\n61662 91083\r\n79719 67952\r\n58392 57838\r\n38770 65651\r\n99179 1444\r\n27076 73037\r\n24406 37147\r\n71315 46540\r\n96032 16397\r\n37940 24702\r\n12296 74528\r\n28358 30908\r\n54553 17283\r\n24624 78495\r\n72966 3679\r\n20387 58765\r\n99945 40943\r\n39375 98919\r\n69827 68083\r\n19229 81487\r\n93281 96038\r\n70344 15436\r\n52774 32519\r\n84181 37638\r\n13308 96936\r\n20814 85044\r\n23354 43747\r\n21742 40544\r\n66...",
      "output": "NO"
    },
    {
      "input": "100000\r\n811427898 149612837\r\n217879535 391765465\r\n312015889 55576076\r\n502109654 898374324\r\n837673438 573395340\r\n73627132 586553484\r\n286135706 730896237\r\n431281781 33123227\r\n339504151 930209651\r\n24273890 199781887\r\n385794915 638445216\r\n593371309 932054501\r\n992432876 910297550\r\n25389817 101036047\r\n811257862 767331709\r\n286599837 33269331\r\n914451415 766556268\r\n610915478 551452236\r\n623679572 956728523\r\n618661475 28959700\r\n80814085 759764998\r\n833412614 23972120\r\n372613615 451160108\r\n952277797 192525025\r\n94180834...",
      "output": "NO"
    },
    {
      "input": "100000\r\n999999310 355111776\r\n999997105 290689749\r\n999987864 955258596\r\n999982734 163575054\r\n651434692 999980277\r\n597911656 999980191\r\n999960800 443687356\r\n355012116 999946655\r\n952336854 999928966\r\n45517282 999922805\r\n179973775 999917316\r\n999905426 632207441\r\n779267314 999892692\r\n999853285 483353930\r\n351154614 999842308\r\n999839008 662236651\r\n999831901 578713992\r\n37200634 999817393\r\n999796351 595469821\r\n978409167 999790283\r\n999780375 660776937\r\n144203481 999777834\r\n768287757 999776002\r\n918829580 999767553\r\n9...",
      "output": "YES"
    },
    {
      "input": "1\r\n1 1",
      "output": "YES"
    },
    {
      "input": "100000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 1000000000\r\n1000000000 100000000...",
      "output": "YES"
    },
    {
      "input": "1000\r\n333088110 399058895\r\n471442144 623620748\r\n176093908 414653268\r\n770359365 858254057\r\n633319617 715407482\r\n665016794 869011244\r\n614998039 728097460\r\n661820264 650103091\r\n173102710 626978094\r\n950877841 428318790\r\n344978412 920365454\r\n515739718 322600461\r\n617786702 607090925\r\n705264492 435749957\r\n841478621 176438831\r\n893713602 103903669\r\n274374042 444064419\r\n848144350 331718571\r\n836893458 238803192\r\n448138699 313429219\r\n731280910 186365026\r\n201817049 552423303\r\n956585425 275500838\r\n455182734 264423359\r\n5...",
      "output": "NO"
    },
    {
      "input": "1000\r\n999612358 975401198\r\n997425998 349380666\r\n996923060 538816737\r\n501153359 996629983\r\n72690789 995750903\r\n994148182 773411331\r\n991991369 174500126\r\n991522505 48213406\r\n405848145 990274385\r\n988761440 970791764\r\n988708124 129738635\r\n988197588 997570595\r\n31519490 987917068\r\n987105175 238478476\r\n986010454 883020776\r\n985752212 532246696\r\n985641509 639604007\r\n984751025 686682241\r\n252527424 982222150\r\n981111254 398155446\r\n979979831 108975167\r\n276528859 979463544\r\n171212031 977534985\r\n975818367 509197838\r\n9750...",
      "output": "YES"
    },
    {
      "input": "1000\r\n827383547 806138830\r\n195005363 487700212\r\n720572685 849457955\r\n185609793 946488207\r\n476967225 307580056\r\n216339239 956267495\r\n805545377 898245762\r\n188401557 151343242\r\n942993592 774041842\r\n356544802 853405673\r\n790675662 58072633\r\n499451173 349801475\r\n385305928 371568491\r\n833559326 117996603\r\n83816325 742273561\r\n403970296 869141853\r\n200504712 972992156\r\n735459662 537710843\r\n718048781 625331572\r\n183766740 872420558\r\n538616782 750994024\r\n466649780 279195291\r\n491894312 911828072\r\n615371497 371206255\r\n799...",
      "output": "NO"
    },
    {
      "input": "1000\r\n116444115 999048089\r\n797179204 993991814\r\n491671684 993467937\r\n992968221 882979747\r\n991691038 258357208\r\n558177241 987979856\r\n987281441 627070680\r\n986648011 828127788\r\n938998084 982695576\r\n378681044 982353872\r\n996198382 981847122\r\n356313375 979809660\r\n35987810 979430931\r\n978729829 664409689\r\n75852311 977369302\r\n974603139 779941489\r\n168007769 974591385\r\n974441917 62295179\r\n982461863 972992156\r\n972636317 591655419\r\n727953990 972026612\r\n971347688 84367969\r\n970868428 683839277\r\n906186211 969682151\r\n55649...",
      "output": "YES"
    },
    {
      "input": "1000\r\n689254958 695899688\r\n768825477 202036572\r\n560018758 724454131\r\n367741336 122617048\r\n533494265 981840496\r\n692228597 123475746\r\n31750380 882993294\r\n274791362 797807586\r\n771362487 268174074\r\n606190401 989803518\r\n220794383 66134150\r\n923354115 787067896\r\n400887274 298049346\r\n936401399 970920202\r\n736219437 13140995\r\n289280503 263845436\r\n106688109 821353375\r\n288943858 932310041\r\n334362889 716892655\r\n591669713 54104261\r\n770707138 626027322\r\n916382044 116035041\r\n732235903 253188011\r\n365494852 477989150\r\n47715...",
      "output": "NO"
    },
    {
      "input": "1000\r\n257487032 998728151\r\n998068957 539945037\r\n294783527 996580402\r\n119581942 994795269\r\n593766732 994316077\r\n342943151 992263000\r\n374608530 991915867\r\n313074874 991379549\r\n991199226 31956535\r\n226761813 989765616\r\n422466640 985699169\r\n274864667 985157062\r\n984680176 480647619\r\n984634161 90340902\r\n708875335 984072727\r\n467827770 982849515\r\n991378827 981840496\r\n980919822 142940821\r\n980356713 857620494\r\n980152660 930379583\r\n979249735 346932813\r\n892207079 979003407\r\n46723418 978807217\r\n977968081 8207287\r\n935627...",
      "output": "YES"
    },
    {
      "input": "1000\r\n867338382 269448532\r\n492388695 476181445\r\n454226114 249721727\r\n3778593 549872879\r\n86713 361133639\r\n620546845 133222402\r\n105665403 314998102\r\n801372655 444271930\r\n918426235 888321852\r\n213750936 623062234\r\n779228372 91104591\r\n907065570 369558509\r\n360535869 870397544\r\n383652313 188986576\r\n123781334 578975724\r\n563912063 559676050\r\n519971489 568161106\r\n397717653 621876535\r\n360742404 513486443\r\n779217590 15951572\r\n978279077 790420252\r\n30261518 698792990\r\n412768981 889515245\r\n820650910 584772045\r\n9684664 23...",
      "output": "NO"
    },
    {
      "input": "1000\r\n998671296 398529950\r\n282710871 997625496\r\n996548626 247638474\r\n994316513 796375626\r\n74400448 994045767\r\n992515301 717643653\r\n122146379 992387486\r\n798021961 991802892\r\n565106474 991293147\r\n990661450 339683798\r\n143702194 990383536\r\n990361907 633607447\r\n988765997 75050531\r\n811239411 988563171\r\n196674166 987295104\r\n10489858 986361181\r\n985958344 959974077\r\n984387836 663777952\r\n732779124 983351773\r\n983103492 828912260\r\n982221682 111135829\r\n405078893 981855920\r\n980947923 559350664\r\n978930592 110228364\r\n4645...",
      "output": "YES"
    },
    {
      "input": "1000\r\n842997376 750454510\r\n485485101 215951913\r\n329222289 794200503\r\n877228615 179907435\r\n35394079 911389560\r\n574216207 672907544\r\n743470017 888146024\r\n182729756 945512081\r\n363245437 65489984\r\n696512437 261502960\r\n961414799 492322593\r\n36001216 396759523\r\n128055095 489650919\r\n91351720 586795944\r\n71151742 144810454\r\n569011394 830071596\r\n218589604 324601399\r\n96426040 311443029\r\n977056512 750271718\r\n735200727 649555110\r\n920465425 515166069\r\n630947039 679646779\r\n230875184 948077868\r\n275806969 541811837\r\n6874383...",
      "output": "NO"
    },
    {
      "input": "1000\r\n539572867 999890705\r\n998167780 170700897\r\n345717613 994186531\r\n32977822 993637878\r\n989902325 114842675\r\n502409563 989116393\r\n988579724 429492741\r\n988358988 282969047\r\n986206121 658064925\r\n984297995 42540375\r\n305129236 984084667\r\n983884261 552158739\r\n519710340 981177977\r\n532137920 979280585\r\n389505702 978098143\r\n977941981 403408843\r\n783345136 977056512\r\n976387308 39390890\r\n974903760 757680859\r\n974151153 727444936\r\n730114652 973848127\r\n972279190 212918003\r\n971152440 922234805\r\n361992545 971127228\r\n9689...",
      "output": "YES"
    },
    {
      "input": "1000\r\n998 1000\r\n1001 999\r\n1000 998\r\n999 997\r\n998 996\r\n997 995\r\n996 994\r\n995 993\r\n994 992\r\n993 991\r\n992 990\r\n991 989\r\n990 988\r\n989 987\r\n988 986\r\n987 985\r\n986 984\r\n985 983\r\n984 982\r\n983 981\r\n982 980\r\n981 979\r\n980 978\r\n979 977\r\n978 976\r\n977 975\r\n976 974\r\n975 973\r\n974 972\r\n973 971\r\n972 970\r\n971 969\r\n970 968\r\n969 967\r\n968 966\r\n967 965\r\n966 964\r\n965 963\r\n964 962\r\n963 961\r\n962 960\r\n961 959\r\n960 958\r\n959 957\r\n958 956\r\n957 955\r\n956 954\r\n955 953\r\n954 952\r\n953 951\r\n952 950\r\n951 949\r\n950 948\r\n949 947\r\n948 946\r\n947 945...",
      "output": "YES"
    },
    {
      "input": "1000\r\n998 1000\r\n1001 999\r\n1000 998\r\n999 997\r\n998 996\r\n997 995\r\n996 994\r\n995 993\r\n994 992\r\n993 991\r\n992 990\r\n991 989\r\n990 988\r\n989 987\r\n988 986\r\n987 985\r\n986 984\r\n985 983\r\n984 982\r\n983 981\r\n982 980\r\n981 979\r\n980 978\r\n979 977\r\n978 976\r\n977 975\r\n976 974\r\n975 973\r\n974 972\r\n973 971\r\n972 970\r\n971 969\r\n970 968\r\n969 967\r\n968 966\r\n967 965\r\n966 964\r\n965 963\r\n964 962\r\n963 961\r\n962 960\r\n961 959\r\n960 958\r\n959 957\r\n958 956\r\n957 955\r\n956 954\r\n955 953\r\n954 952\r\n953 951\r\n952 950\r\n951 949\r\n950 948\r\n949 947\r\n948 946\r\n947 945...",
      "output": "NO"
    },
    {
      "input": "100000\r\n137472638 462604622\r\n503287457 601670570\r\n865688118 789337739\r\n629275071 135927815\r\n291250006 682079042\r\n331889459 641266293\r\n886323979 964192759\r\n458255581 522671965\r\n555351728 867307681\r\n843588144 729683946\r\n975238372 159244276\r\n744479273 119471396\r\n18341008 133357110\r\n341362675 89138854\r\n632144963 492219244\r\n79218182 903314978\r\n133842801 625561654\r\n915350982 754239825\r\n470865957 690507784\r\n338842881 279175918\r\n287778504 508733701\r\n552424048 427176501\r\n414746266 795690776\r\n636056965 997321127\r\n11...",
      "output": "NO"
    },
    {
      "input": "100000\r\n999997007 877407014\r\n152205009 999991979\r\n72170911 999976136\r\n999973612 62792035\r\n281093561 999973220\r\n788237456 999942226\r\n720269976 999940366\r\n462369172 999912448\r\n170975984 999910628\r\n840931671 999880420\r\n775763222 999875191\r\n965785675 999874853\r\n999850583 2287529\r\n999821779 720274473\r\n999821622 443216346\r\n331432666 999818793\r\n223004289 999812911\r\n999808473 613266721\r\n999793364 421181311\r\n999790475 437765860\r\n999783770 13026076\r\n790466094 999775739\r\n999755800 69859686\r\n999752579 929369399\r\n99974...",
      "output": "YES"
    },
    {
      "input": "100000\r\n935655342 711021482\r\n217623818 325233788\r\n705134190 814077019\r\n956630806 17089361\r\n907585558 61372185\r\n227484290 533993262\r\n657505890 108996088\r\n689869578 169136309\r\n407448180 342231267\r\n362942662 451148679\r\n872338497 550581284\r\n168382216 701962010\r\n602867380 785860235\r\n486948222 754094786\r\n903012397 439589652\r\n323453628 939093321\r\n324179768 890283093\r\n468835177 148839023\r\n267459744 161597700\r\n703457777 63956210\r\n383222623 934997556\r\n64363255 56585117\r\n36032367 51073501\r\n796245727 104104023\r\n501822...",
      "output": "NO"
    },
    {
      "input": "100000\r\n999997363 398446583\r\n999995145 410988845\r\n999990530 462952441\r\n999988057 273754198\r\n999986803 420748578\r\n417693435 999962293\r\n999952458 23208932\r\n999936514 828783757\r\n999933696 361589753\r\n999915525 246674043\r\n999896644 108557119\r\n999877056 146057714\r\n403567821 999875320\r\n999871232 441660533\r\n44233779 999867501\r\n999862248 518292199\r\n847974884 999861346\r\n198405913 999854100\r\n999851713 197352244\r\n999850162 854382595\r\n999849547 701476214\r\n999849108 825453864\r\n410321180 999844433\r\n999838743 980347869\r\n7...",
      "output": "YES"
    },
    {
      "input": "100000\r\n284570326 818771470\r\n491768690 753829710\r\n249612967 394105898\r\n193218202 138762350\r\n669145301 735632625\r\n441129769 668478096\r\n891476710 85977804\r\n71226680 670376460\r\n962379045 699736121\r\n141425570 498900703\r\n275667301 880400014\r\n592285158 434195727\r\n553379461 927153458\r\n739533399 461794193\r\n763814423 237216956\r\n239159949 593849175\r\n206531898 317765179\r\n872576268 838405517\r\n799212316 482944511\r\n422706932 229261026\r\n727440800 402935736\r\n411003082 141741496\r\n571341254 687400735\r\n546369082 356111110\r\n3...",
      "output": "NO"
    },
    {
      "input": "100000\r\n999998651 919486151\r\n999970388 229581192\r\n708509779 999965374\r\n924907848 999948672\r\n705627787 999941554\r\n999929332 752182118\r\n999922800 61306672\r\n999916027 344941446\r\n992395011 999908361\r\n797640606 999889911\r\n999884236 441351016\r\n999871124 31362458\r\n804848114 999864420\r\n999863619 163046593\r\n495508108 999859517\r\n264960245 999824336\r\n999823424 472945479\r\n78512402 999817775\r\n999816820 268490473\r\n830807842 999815680\r\n999808875 830117839\r\n999800799 5665827\r\n999800536 160848082\r\n999799898 471517827\r\n9997...",
      "output": "YES"
    },
    {
      "input": "100000\r\n701887598 858119171\r\n501072346 622617120\r\n939315936 123877881\r\n369347044 466118085\r\n114925768 430705045\r\n83425060 109471901\r\n369225526 968924627\r\n157616485 611808100\r\n582526823 846799869\r\n401428535 69651582\r\n145977509 593494235\r\n575996612 311653637\r\n761090175 396663729\r\n19750496 137342768\r\n34681857 479554660\r\n864244721 99035088\r\n962972191 871159101\r\n527972010 571284656\r\n595806103 804291323\r\n99598547 846988791\r\n374659852 422648850\r\n924152442 620196855\r\n811682845 178503778\r\n1525141 167926710\r\n7121060...",
      "output": "NO"
    },
    {
      "input": "100000\r\n295301528 999994660\r\n488365028 999988267\r\n99291309 999985766\r\n999973489 135870011\r\n999969853 990506996\r\n999955913 381638097\r\n364245628 999951468\r\n861099135 999928067\r\n999924827 477976077\r\n999915029 203382978\r\n774144914 999890672\r\n999876293 506601793\r\n206128406 999865743\r\n999853869 884432653\r\n241749734 999838422\r\n999834635 451819778\r\n999831811 657724587\r\n999801704 103843083\r\n749694110 999792511\r\n102200385 999768201\r\n999768185 223600680\r\n185877789 999758319\r\n999743759 206342279\r\n999742195 257655081\r\n...",
      "output": "YES"
    },
    {
      "input": "100000\r\n431668015 879971022\r\n346180339 70184515\r\n483794713 853649865\r\n648249629 545475885\r\n84153504 487232085\r\n845433002 990561567\r\n46372544 797697441\r\n979165074 113048252\r\n993863618 57450408\r\n702910298 154213263\r\n306588457 16287717\r\n43887354 704932259\r\n720949807 528609401\r\n727449903 535152137\r\n600516586 572149261\r\n399101715 429607563\r\n864744512 574188292\r\n217538504 829801555\r\n687367187 125638134\r\n566237946 824711876\r\n442361964 726911607\r\n974614820 561339195\r\n52024435 814831012\r\n456681199 569676901\r\n244635...",
      "output": "NO"
    },
    {
      "input": "100000\r\n816341096 999996770\r\n999984245 306957376\r\n999977211 490072839\r\n492056365 999963130\r\n130162012 999925965\r\n861350972 999916288\r\n107376072 999908535\r\n999903756 377256824\r\n999903324 108781334\r\n999896755 904092645\r\n999884050 106938811\r\n686873833 999858430\r\n902375994 999842762\r\n310851417 999831971\r\n999826513 693024063\r\n638679311 999820641\r\n999818855 282695182\r\n999806452 688982275\r\n820832339 999805039\r\n999800304 223849824\r\n999785278 57275010\r\n999774525 71122455\r\n251836477 999773702\r\n999770137 748825039\r\n3...",
      "output": "YES"
    },
    {
      "input": "100000\r\n99998 100000\r\n100001 99999\r\n100000 99998\r\n99999 99997\r\n99998 99996\r\n99997 99995\r\n99996 99994\r\n99995 99993\r\n99994 99992\r\n99993 99991\r\n99992 99990\r\n99991 99989\r\n99990 99988\r\n99989 99987\r\n99988 99986\r\n99987 99985\r\n99986 99984\r\n99985 99983\r\n99984 99982\r\n99983 99981\r\n99982 99980\r\n99981 99979\r\n99980 99978\r\n99979 99977\r\n99978 99976\r\n99977 99975\r\n99976 99974\r\n99975 99973\r\n99974 99972\r\n99973 99971\r\n99972 99970\r\n99971 99969\r\n99970 99968\r\n99969 99967\r\n99968 99966\r\n99967 99965\r\n99966 99964\r\n99965 99963\r\n99964 ...",
      "output": "YES"
    },
    {
      "input": "100000\r\n99998 100000\r\n100001 99999\r\n100000 99998\r\n99999 99997\r\n99998 99996\r\n99997 99995\r\n99996 99994\r\n99995 99993\r\n99994 99992\r\n99993 99991\r\n99992 99990\r\n99991 99989\r\n99990 99988\r\n99989 99987\r\n99988 99986\r\n99987 99985\r\n99986 99984\r\n99985 99983\r\n99984 99982\r\n99983 99981\r\n99982 99980\r\n99981 99979\r\n99980 99978\r\n99979 99977\r\n99978 99976\r\n99977 99975\r\n99976 99974\r\n99975 99973\r\n99974 99972\r\n99973 99971\r\n99972 99970\r\n99971 99969\r\n99970 99968\r\n99969 99967\r\n99968 99966\r\n99967 99965\r\n99966 99964\r\n99965 99963\r\n99964 ...",
      "output": "NO"
    },
    {
      "input": "4\r\n10 10\r\n8 8\r\n8 15\r\n9 9",
      "output": "NO"
    },
    {
      "input": "4\r\n10 10\r\n8 8\r\n8 9\r\n9 9",
      "output": "NO"
    },
    {
      "input": "3\r\n3 4\r\n4 5\r\n5 5",
      "output": "NO"
    },
    {
      "input": "3\r\n10 10\r\n5 5\r\n10 10",
      "output": "NO"
    },
    {
      "input": "3\r\n5 5\r\n4 6\r\n5 5",
      "output": "NO"
    },
    {
      "input": "3\r\n5 7\r\n3 9\r\n8 10",
      "output": "NO"
    },
    {
      "input": "3\r\n10 10\r\n1 1\r\n2 2",
      "output": "NO"
    },
    {
      "input": "3\r\n3 5\r\n1 2\r\n3 4",
      "output": "NO"
    },
    {
      "input": "100000\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5\r\n5 5...",
      "output": "NO"
    },
    {
      "input": "3\r\n4 8\r\n6 25\r\n12 12",
      "output": "NO"
    },
    {
      "input": "3\r\n3 5\r\n4 10\r\n6 6",
      "output": "NO"
    },
    {
      "input": "3\r\n200 200\r\n300 20\r\n50 50",
      "output": "NO"
    },
    {
      "input": "3\r\n5 3\r\n6 4\r\n5 5",
      "output": "NO"
    },
    {
      "input": "4\r\n5 5\r\n4 6\r\n4 4\r\n5 5",
      "output": "NO"
    },
    {
      "input": "3\r\n10 10\r\n1 100\r\n20 20",
      "output": "NO"
    },
    {
      "input": "4\r\n1 3\r\n2 4\r\n3 5\r\n4 6",
      "output": "NO"
    },
    {
      "input": "3\r\n1 60\r\n70 55\r\n56 80",
      "output": "NO"
    },
    {
      "input": "3\r\n5 6\r\n5 7\r\n6 8",
      "output": "NO"
    },
    {
      "input": "3\r\n6 6\r\n5 7\r\n6 6",
      "output": "NO"
    }
  ],
  "reference_solution": {
    "submission_id": 319911003,
    "submission_url": "https://codeforces.com/contest/1008/submission/319911003",
    "author_handle": "aneraserOvO",
    "author_rating": null,
    "language": "C++23 (GCC 14-64, msys2)",
    "code": "#include <iostream>\n#include <utility>\n#include <algorithm>\n using namespace std;\n int main() {\n int n; cin >> n;\n int a, b; cin >> a >> b;\n int t = max(a, b);\n while(--n) {\n  cin >> a >> b;\n  if(a > b) swap(a, b);\n  if(a > t) {\n   cout << \"NO\" << endl;\n   return 0;\n  } else if(b > t) {\n   t = a;\n  } else {\n   t = b;\n  }\n }\n cout << \"YES\" << endl;\n  return 0;\n}"
  },
  "verified_pseudocode": "// O(N) time, O(1) space\nfunction solve():\n  Read N\n\n  // Read dimensions of the first rectangle\n  Read w_0, h_0\n\n  // Initialize 'prev_height_limit' with the maximum possible height for the first rectangle.\n  // Since there's no preceding rectangle, we can always pick the larger dimension\n  // to give more room for the following rectangles.\n  prev_height_limit = max(w_0, h_0)\n\n  // Iterate through the remaining N-1 rectangles\n  For i from 1 to N-1:\n    Read current_w, current_h\n\n    // Ensure 'current_min' holds the smaller dimension and 'current_max' holds the larger.\n    current_min = min(current_w, current_h)\n    current_max = max(current_w, current_h)\n\n    // Case 1: If even the smaller dimension is too large (greater than 'prev_height_limit'),\n    // it's impossible to maintain non-ascending order. Output 'NO' and terminate.\n    If current_min > prev_height_limit:\n      Print \"NO\"\n      Return\n    // Case 2: If the larger dimension ('current_max') is too large,\n    // but the smaller dimension ('current_min') is acceptable.\n    // We are forced to choose the smaller dimension for the current rectangle.\n    Else if current_max > prev_height_limit:\n      prev_height_limit = current_min\n    // Case 3: Both dimensions ('current_min' and 'current_max') are acceptable.\n    // To maximize flexibility for future rectangles, we choose the largest possible valid height,\n    // which is 'current_max'.\n    Else:\n      prev_height_limit = current_max\n\n  // If the loop completes, it means a valid sequence of heights was found for all rectangles.\n  // Output 'YES'.\n  Print \"YES\"",
  "verified_solution_code": "#include <bits/stdc++.h>\n\nusing namespace std;\n\nint solve() {\n    int N;\n    cin >> N;\n\n    int prev_height_limit;\n    cin >> prev_height_limit;\n    int h0;\n    cin >> h0;\n    prev_height_limit = max(prev_height_limit, h0);\n\n    for(int i = 1; i < N; i++) {\n        int current_w, current_h;\n        cin >> current_w >> current_h;\n\n        int current_min = min(current_w, current_h);\n        int current_max = max(current_w, current_h);\n\n        if(current_min > prev_height_limit) {\n            cout << \"NO\" << endl;\n            return 0;\n        } else if(current_max > prev_height_limit) {\n            prev_height_limit = current_min;\n        } else {\n            prev_height_limit = current_max;\n        }\n    }\n\n    cout << \"YES\" << endl;\n\n    return 0;\n}\n\nint main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n\n    solve();\n\n    return 0;\n}",
  "code_quality_analysis": {
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {
      "oracle_0": {
        "rating": "Excellent",
        "justification": "This solution implements the optimal greedy strategy. It iterates through the rectangles once, maintaining the maximum height allowed for the current rectangle based on the previous one. For each rectangle (w, h), it first sorts w and h to ensure w <= h. Then, it applies the greedy logic:\n1. If even the smaller dimension (w) is greater than the previously chosen height ('t'), it's impossible. Print 'NO'.\n2. If the larger dimension (h) is greater than 't', but the smaller dimension (w) is not, we must choose 'w' as the current rectangle's height. Update 't = w'.\n3. If both dimensions (w and h) are less than or equal to 't', we choose 'h' (the larger one) to maximize flexibility for subsequent rectangles. Update 't = h'.\nThis approach is O(N) time and O(1) space, handling all constraints and edge cases correctly."
      }
    }
  }
}
```

## Problem: 1020A

```json
{
  "problem_id": "1020A",
  "problem_url": "https://codeforces.com/problemset/problem/1020/A",
  "problem_metadata": {
    "name": "New Building for SIS",
    "tags": [
      "math"
    ],
    "time_limit_ms": 1000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">A. New Building for SIS</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>1 second</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\"><div class=\"property-title\">input</div>standard input</div><div class=\"output-file output-standard\"><div class=\"property-title\">output</div>standard output</div></div><div><p>You are looking at the floor plan of the Summer Informatics School's new building. You were tasked with SIS logistics, so you really care about travel time between different locations: it is important to know how long it would take to get from the lecture room to the canteen, or from the gym to the server room.</p><p>The building consists of <span class=\"tex-span\"><i>n</i></span> towers, <span class=\"tex-span\"><i>h</i></span> floors each, where the towers are labeled from <span class=\"tex-span\">1</span> to <span class=\"tex-span\"><i>n</i></span>, the floors are labeled from <span class=\"tex-span\">1</span> to <span class=\"tex-span\"><i>h</i></span>. There is a passage between any two adjacent towers (two towers <span class=\"tex-span\"><i>i</i></span> and <span class=\"tex-span\"><i>i</i>\u2009+\u20091</span> for all <span class=\"tex-span\"><i>i</i></span>: <span class=\"tex-span\">1\u2009\u2264\u2009<i>i</i>\u2009\u2264\u2009<i>n</i>\u2009-\u20091</span>) on every floor <span class=\"tex-span\"><i>x</i></span>, where <span class=\"tex-span\"><i>a</i>\u2009\u2264\u2009<i>x</i>\u2009\u2264\u2009<i>b</i></span>. It takes exactly one minute to walk between any two adjacent floors of a tower, as well as between any two adjacent towers, provided that there is a passage on that floor. It is not permitted to leave the building.</p><center> <img class=\"tex-graphics\" height=\"208px\" src=\"https://espresso.codeforces.com/71bee3824e804a2c4c354c10dc0bf8fe060716dc.png\" style=\"max-width: 100.0%;max-height: 100.0%;\" width=\"265px\"/><p><span class=\"tex-font-size-small\">The picture illustrates the first example.</span> </p></center><p>You have given <span class=\"tex-span\"><i>k</i></span> pairs of locations <span class=\"tex-span\">(<i>t</i><sub class=\"lower-index\"><i>a</i></sub>,\u2009<i>f</i><sub class=\"lower-index\"><i>a</i></sub>)</span>, <span class=\"tex-span\">(<i>t</i><sub class=\"lower-index\"><i>b</i></sub>,\u2009<i>f</i><sub class=\"lower-index\"><i>b</i></sub>)</span>: floor <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>a</i></sub></span> of tower <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>a</i></sub></span> and floor <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>b</i></sub></span> of tower <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>b</i></sub></span>. For each pair you need to determine the minimum walking time between these locations.</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line of the input contains following integers:</p><ul> <li> <span class=\"tex-span\"><i>n</i></span>: the number of towers in the building (<span class=\"tex-span\">1\u2009\u2264\u2009<i>n</i>\u2009\u2264\u200910<sup class=\"upper-index\">8</sup></span>), </li><li> <span class=\"tex-span\"><i>h</i></span>: the number of floors in each tower (<span class=\"tex-span\">1\u2009\u2264\u2009<i>h</i>\u2009\u2264\u200910<sup class=\"upper-index\">8</sup></span>), </li><li> <span class=\"tex-span\"><i>a</i></span> and <span class=\"tex-span\"><i>b</i></span>: the lowest and highest floor where it's possible to move between adjacent towers (<span class=\"tex-span\">1\u2009\u2264\u2009<i>a</i>\u2009\u2264\u2009<i>b</i>\u2009\u2264\u2009<i>h</i></span>), </li><li> <span class=\"tex-span\"><i>k</i></span>: total number of queries (<span class=\"tex-span\">1\u2009\u2264\u2009<i>k</i>\u2009\u2264\u200910<sup class=\"upper-index\">4</sup></span>). </li></ul><p>Next <span class=\"tex-span\"><i>k</i></span> lines contain description of the queries. Each description consists of four integers <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>a</i></sub></span>, <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>a</i></sub></span>, <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>b</i></sub></span>, <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>b</i></sub></span> (<span class=\"tex-span\">1\u2009\u2264\u2009<i>t</i><sub class=\"lower-index\"><i>a</i></sub>,\u2009<i>t</i><sub class=\"lower-index\"><i>b</i></sub>\u2009\u2264\u2009<i>n</i></span>, <span class=\"tex-span\">1\u2009\u2264\u2009<i>f</i><sub class=\"lower-index\"><i>a</i></sub>,\u2009<i>f</i><sub class=\"lower-index\"><i>b</i></sub>\u2009\u2264\u2009<i>h</i></span>). This corresponds to a query to find the minimum travel time between <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>a</i></sub></span>-th floor of the <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>a</i></sub></span>-th tower and <span class=\"tex-span\"><i>f</i><sub class=\"lower-index\"><i>b</i></sub></span>-th floor of the <span class=\"tex-span\"><i>t</i><sub class=\"lower-index\"><i>b</i></sub></span>-th tower.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>For each query print a single integer: the minimum walking time between the locations in minutes.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Example</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>3 6 2 3 3<br/>1 2 1 3<br/>1 4 3 4<br/>1 2 2 3<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>1<br/>4<br/>2<br/></pre></div></div></div></div>",
  "pretests": [
    {
      "input": "3 6 2 3 3\r\n1 2 1 3\r\n1 4 3 4\r\n1 2 2 3",
      "output": "1\r\n4\r\n2"
    },
    {
      "input": "1 1 1 1 1\r\n1 1 1 1",
      "output": "0"
    },
    {
      "input": "10 1 1 1 100\r\n1 1 1 1\r\n1 1 2 1\r\n1 1 3 1\r\n1 1 4 1\r\n1 1 5 1\r\n1 1 6 1\r\n1 1 7 1\r\n1 1 8 1\r\n1 1 9 1\r\n1 1 10 1\r\n2 1 1 1\r\n2 1 2 1\r\n2 1 3 1\r\n2 1 4 1\r\n2 1 5 1\r\n2 1 6 1\r\n2 1 7 1\r\n2 1 8 1\r\n2 1 9 1\r\n2 1 10 1\r\n3 1 1 1\r\n3 1 2 1\r\n3 1 3 1\r\n3 1 4 1\r\n3 1 5 1\r\n3 1 6 1\r\n3 1 7 1\r\n3 1 8 1\r\n3 1 9 1\r\n3 1 10 1\r\n4 1 1 1\r\n4 1 2 1\r\n4 1 3 1\r\n4 1 4 1\r\n4 1 5 1\r\n4 1 6 1\r\n4 1 7 1\r\n4 1 8 1\r\n4 1 9 1\r\n4 1 10 1\r\n5 1 1 1\r\n5 1 2 1\r\n5 1 3 1\r\n5 1 4 1\r\n5 1 5 1\r\n5 1 6 1\r\n5 1 7 1\r\n5 1 8 1\r\n5 1 9 1\r\n5 1 10 1\r\n6 1 1 1\r\n6 1 2 1\r\n6 1 3 1\r\n6 1 4 1\r\n6 1 5 ...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n6\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n7\r\n6\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n8\r\n7\r\n6\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n9\r\n8\r\n7\r\n6\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0"
    },
    {
      "input": "3 10 3 5 900\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 1 3\r\n1 2 1 4\r\n1 2 1 5\r\n1 2 1 6\r\n1 2 1 7\r\n1 2 1 8\r\n1 2 1 9\r\n1 2 1 10\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 2 3\r\n1 2 2 4\r\n1 2 2 5\r\n1 2 2 6\r\n1 2 2 7\r\n1 2 2 8\r\n1 2 2 9\r\n1 2 2 10\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 3 3\r\n1 2 3 4\r\n1 2 3 ...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n5\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n6\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n5\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n5\r\n4\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n6\r\n5\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n6\r\n5\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n..."
    },
    {
      "input": "3 10 1 10 900\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 1 3\r\n1 2 1 4\r\n1 2 1 5\r\n1 2 1 6\r\n1 2 1 7\r\n1 2 1 8\r\n1 2 1 9\r\n1 2 1 10\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 2 3\r\n1 2 2 4\r\n1 2 2 5\r\n1 2 2 6\r\n1 2 2 7\r\n1 2 2 8\r\n1 2 2 9\r\n1 2 2 10\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 3 3\r\n1 2 3 4\r\n1 2 3...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n5\r\n4\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n6\r\n5\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n6\r\n5\r\n4\r\n3\r\n2\r\n1\r\n2\r\n3\r\n4\r\n..."
    },
    {
      "input": "6 15 13 13 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 1 11\r\n1 1 1 12\r\n1 1 1 13\r\n1 1 1 14\r\n1 1 1 15\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 2 11\r\n1 1 2 12\r\n1 1 2 13\r\n1 1 2 14\r\n1 1 2 15\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 1 3 11\r\n1 1 3 12\r\n1 1 3 13\r\n1 1 3 14\r\n1 1 3 15\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 4 7\r\n1 1 4 8\r...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n14\r\n15\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n15\r\n16\r\n27\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n16\r\n17\r\n28\r\n27\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n17\r\n18\r\n29\r\n28\r\n27\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n12\r\n13\r\n14\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n..."
    },
    {
      "input": "100000000 100000000 77777777 99999999 10000\r\n52734045 43343967 91011672 73768545\r\n21790053 90211597 67340762 8250031\r\n24044899 62998793 6713109 57209480\r\n89691587 81568441 19189392 6826234\r\n70013637 30045812 52909796 80677960\r\n33399549 84055048 68500031 3988584\r\n45704401 52047669 50628834 62126725\r\n39766526 17191727 81768099 6502269\r\n41352724 60903968 58736236 29890915\r\n70386933 20446371 26841274 59582206\r\n46199386 97177418 57843999 82216777\r\n38707022 61698842 84371648 2229489\r\n46378417 88455434 40497367 7...",
      "output": "76720669\r\n127512275\r\n52679071\r\n145244402\r\n67735989\r\n115166946\r\n46305593\r\n173863131\r\n82144183\r\n119072636\r\n26605254\r\n137291849\r\n17598730\r\n97995331\r\n123213989\r\n115163733\r\n80701169\r\n75910968\r\n95938328\r\n157963451\r\n7502271\r\n77847817\r\n108972692\r\n60215963\r\n144546315\r\n118627943\r\n133202834\r\n151536361\r\n62313726\r\n36601623\r\n142620392\r\n114857275\r\n44469801\r\n145037534\r\n139985945\r\n173735433\r\n68517051\r\n28997181\r\n73894388\r\n70310035\r\n103799318\r\n86126355\r\n87520907\r\n115722090\r\n84731860\r\n75752152\r\n91710723\r\n114533423\r\n106643773\r..."
    },
    {
      "input": "3 10 7 9 900\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 1 3\r\n1 2 1 4\r\n1 2 1 5\r\n1 2 1 6\r\n1 2 1 7\r\n1 2 1 8\r\n1 2 1 9\r\n1 2 1 10\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 2 3\r\n1 2 2 4\r\n1 2 2 5\r\n1 2 2 6\r\n1 2 2 7\r\n1 2 2 8\r\n1 2 2 9\r\n1 2 2 10\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 3 3\r\n1 2 3 4\r\n1 2 3 ...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n13\r\n12\r\n11\r\n10\r\n9\r\n8\r\n7\r\n8\r\n9\r\n10\r\n14\r\n13\r\n12\r\n11\r\n10\r\n9\r\n8\r\n9\r\n10\r\n11\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n12\r\n11\r\n10\r\n9\r\n8\r\n7\r\n6\r\n7\r\n8\r\n9\r\n13\r\n12\r\n11\r\n10\r\n9\r\n8\r\n7\r\n8\r\n9\r\n10\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n11\r\n10\r\n9\r\n8\r\n7\r\n6\r\n5\r\n6\r\n7\r\n8\r\n12\r\n11\r\n10\r\n9\r\n8\r\n7\r\n6\r\n7\r\n8\r\n9\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n10\r\n9\r\n8\r\n7\r\n6\r\n5\r\n4\r\n5\r\n6\r\n7\r\n11\r\n10\r\n9\r\n8\r\n7\r\n6\r\n5\r\n6\r\n7\r\n8\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n9\r\n8\r\n7\r\n6\r\n5\r\n4\r\n3\r\n4\r\n5\r\n6\r\n10\r\n9\r\n8\r\n7\r\n6\r\n5\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n3\r\n2\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n8\r..."
    },
    {
      "input": "6 15 12 15 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 1 11\r\n1 1 1 12\r\n1 1 1 13\r\n1 1 1 14\r\n1 1 1 15\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 2 11\r\n1 1 2 12\r\n1 1 2 13\r\n1 1 2 14\r\n1 1 2 15\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 1 3 11\r\n1 1 3 12\r\n1 1 3 13\r\n1 1 3 14\r\n1 1 3 15\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 4 7\r\n1 1 4 8\r...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n12\r\n13\r\n14\r\n15\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n14\r\n15\r\n16\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n15\r\n16\r\n17\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n16\r\n17\r\n18\r\n27\r\n26\r\n25\r\n24\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n12\r\n11\r\n12\r\n13\r\n14\r\n23\r\n22\r\n21\r\n20\r\n19\r\n18\r\n17\r\n16\r\n15\r\n14\r\n13\r\n12\r\n13\r\n..."
    },
    {
      "input": "6 15 1 14 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 1 11\r\n1 1 1 12\r\n1 1 1 13\r\n1 1 1 14\r\n1 1 1 15\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 2 11\r\n1 1 2 12\r\n1 1 2 13\r\n1 1 2 14\r\n1 1 2 15\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 1 3 11\r\n1 1 3 12\r\n1 1 3 13\r\n1 1 3 14\r\n1 1 3 15\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 4 7\r\n1 1 4 8\r\n...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15..."
    },
    {
      "input": "6 15 2 7 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n1 1 1 8\r\n1 1 1 9\r\n1 1 1 10\r\n1 1 1 11\r\n1 1 1 12\r\n1 1 1 13\r\n1 1 1 14\r\n1 1 1 15\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 2 7\r\n1 1 2 8\r\n1 1 2 9\r\n1 1 2 10\r\n1 1 2 11\r\n1 1 2 12\r\n1 1 2 13\r\n1 1 2 14\r\n1 1 2 15\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 3 7\r\n1 1 3 8\r\n1 1 3 9\r\n1 1 3 10\r\n1 1 3 11\r\n1 1 3 12\r\n1 1 3 13\r\n1 1 3 14\r\n1 1 3 15\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 4 7\r\n1 1 4 8\r\n1...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15..."
    },
    {
      "input": "15 6 2 3 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 5 3\r\n1 1 5 4\r\n1 1 5 5\r\n1 1 5 6\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 6 3\r\n1 1 6 4\r\n1 1 6 5\r\n1 1 6 6\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 7 3\r\n1 1 7 4\r\n1 1 7 5\r\n1 1 7 6\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 8 3\r\n1 1 8 4\r\n1 1 8 5\r\n1 1 8 6\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 9 3\r\n1 1 9 4\r\n1 1 9 5\r\n1 1 9 6\r\n1 1 10 1\r\n...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n8\r\n7\r\n8\r\n9\r\n10\r\n11\r\n9\r\n8\r\n9\r\n10\r\n11\r\n12\r\n10\r\n9\r\n10\r\n11\r\n12\r\n13\r\n11\r\n10\r\n11\r\n12\r\n13\r\n14\r\n12\r\n11\r\n12\r\n13\r\n14\r\n15\r\n13\r\n12\r\n13\r\n14\r\n15\r\n16\r\n14\r\n13\r\n14\r\n15\r\n16\r\n17\r\n15\r\n14\r\n15\r\n16\r\n17\r\n18\r\n16\r\n15\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n8\r\n7\r\n8\r\n9\r\n10\r\n11\r\n9\r\n8\r\n9\r\n10\r\n11\r\n12\r\n10\r\n9\r\n10\r\n11\r\n12\r\n13\r\n11\r..."
    },
    {
      "input": "15 6 3 3 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 5 3\r\n1 1 5 4\r\n1 1 5 5\r\n1 1 5 6\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 6 3\r\n1 1 6 4\r\n1 1 6 5\r\n1 1 6 6\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 7 3\r\n1 1 7 4\r\n1 1 7 5\r\n1 1 7 6\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 8 3\r\n1 1 8 4\r\n1 1 8 5\r\n1 1 8 6\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 9 3\r\n1 1 9 4\r\n1 1 9 5\r\n1 1 9 6\r\n1 1 10 1\r\n...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n5\r\n4\r\n3\r\n4\r\n5\r\n6\r\n6\r\n5\r\n4\r\n5\r\n6\r\n7\r\n7\r\n6\r\n5\r\n6\r\n7\r\n8\r\n8\r\n7\r\n6\r\n7\r\n8\r\n9\r\n9\r\n8\r\n7\r\n8\r\n9\r\n10\r\n10\r\n9\r\n8\r\n9\r\n10\r\n11\r\n11\r\n10\r\n9\r\n10\r\n11\r\n12\r\n12\r\n11\r\n10\r\n11\r\n12\r\n13\r\n13\r\n12\r\n11\r\n12\r\n13\r\n14\r\n14\r\n13\r\n12\r\n13\r\n14\r\n15\r\n15\r\n14\r\n13\r\n14\r\n15\r\n16\r\n16\r\n15\r\n14\r\n15\r\n16\r\n17\r\n17\r\n16\r\n15\r\n16\r\n17\r\n18\r\n18\r\n17\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n4\r\n3\r\n2\r\n3\r\n4\r\n5\r\n5\r\n4\r\n3\r\n4\r\n5\r\n6\r\n6\r\n5\r\n4\r\n5\r\n6\r\n7\r\n7\r\n6\r\n5\r\n6\r\n7\r\n8\r\n8\r\n7\r\n6\r\n7\r\n8\r\n9\r\n9\r\n8\r\n7\r\n8\r\n9\r\n10\r\n10\r\n9\r\n8\r\n9\r\n10\r\n11\r\n11\r\n10\r\n9\r\n10\r\n11\r\n12\r\n12\r\n11\r\n10\r\n11\r\n12\r..."
    },
    {
      "input": "15 6 1 6 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 5 3\r\n1 1 5 4\r\n1 1 5 5\r\n1 1 5 6\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 6 3\r\n1 1 6 4\r\n1 1 6 5\r\n1 1 6 6\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 7 3\r\n1 1 7 4\r\n1 1 7 5\r\n1 1 7 6\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 8 3\r\n1 1 8 4\r\n1 1 8 5\r\n1 1 8 6\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 9 3\r\n1 1 9 4\r\n1 1 9 5\r\n1 1 9 6\r\n1 1 10 1\r\n...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n8\r\n7\r\n8\r\n9\r\n10\r\n11\r\n9\r\n8\r\n9\r\n10\r\n11\r\n12\r\n10\r\n9\r\n10\r\n11\r\n12\r\n13\r\n11\r\n1..."
    },
    {
      "input": "15 6 2 5 8100\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 2 3\r\n1 1 2 4\r\n1 1 2 5\r\n1 1 2 6\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 3 3\r\n1 1 3 4\r\n1 1 3 5\r\n1 1 3 6\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 4 3\r\n1 1 4 4\r\n1 1 4 5\r\n1 1 4 6\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 5 3\r\n1 1 5 4\r\n1 1 5 5\r\n1 1 5 6\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 6 3\r\n1 1 6 4\r\n1 1 6 5\r\n1 1 6 6\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 7 3\r\n1 1 7 4\r\n1 1 7 5\r\n1 1 7 6\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 8 3\r\n1 1 8 4\r\n1 1 8 5\r\n1 1 8 6\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 9 3\r\n1 1 9 4\r\n1 1 9 5\r\n1 1 9 6\r\n1 1 10 1\r\n...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n8\r\n7\r\n8\r\n9\r\n10\r\n11\r\n9\r\n8\r\n9\r\n10\r\n11\r\n12\r\n10\r\n9\r\n10\r\n11\r\n12\r\n13\r\n11\r\n10\r\n11\r\n12\r\n13\r\n14\r\n12\r\n11\r\n12\r\n13\r\n14\r\n15\r\n13\r\n12\r\n13\r\n14\r\n15\r\n16\r\n14\r\n13\r\n14\r\n15\r\n16\r\n17\r\n15\r\n14\r\n15\r\n16\r\n17\r\n18\r\n16\r\n15\r\n16\r\n17\r\n18\r\n19\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n2\r\n1\r\n2\r\n3\r\n4\r\n5\r\n3\r\n2\r\n3\r\n4\r\n5\r\n6\r\n4\r\n3\r\n4\r\n5\r\n6\r\n7\r\n5\r\n4\r\n5\r\n6\r\n7\r\n8\r\n6\r\n5\r\n6\r\n7\r\n8\r\n9\r\n7\r\n6\r\n7\r\n8\r\n9\r\n10\r\n8\r\n7\r\n8\r\n9\r\n10\r\n11\r\n9\r\n8\r\n9\r\n10\r\n11\r\n12\r\n10\r\n9\r\n10\r\n11\r\n12\r\n13\r\n11\r..."
    },
    {
      "input": "100 100 1 2 10000\r\n54 1 21 1\r\n93 1 73 2\r\n12 1 89 3\r\n66 1 99 4\r\n66 1 90 5\r\n12 1 49 6\r\n87 1 52 7\r\n13 1 86 8\r\n20 1 87 9\r\n47 1 27 10\r\n73 1 97 11\r\n41 1 6 12\r\n38 1 30 13\r\n59 1 63 14\r\n3 1 55 15\r\n54 1 75 16\r\n91 1 26 17\r\n38 1 60 18\r\n1 1 10 19\r\n43 1 46 20\r\n14 1 18 21\r\n21 1 13 22\r\n76 1 59 23\r\n67 1 36 24\r\n71 1 86 25\r\n71 1 35 26\r\n67 1 39 27\r\n72 1 59 28\r\n7 1 20 29\r\n63 1 27 30\r\n81 1 96 31\r\n51 1 35 32\r\n12 1 42 33\r\n86 1 40 34\r\n68 1 35 35\r\n77 1 46 36\r\n77 1 91 37\r\n8 1 49 38\r\n48 1 53 39\r\n47 1 12 40\r\n97 1 97 41\r\n10 1 48 42\r\n95...",
      "output": "33\r\n21\r\n79\r\n36\r\n28\r\n42\r\n41\r\n80\r\n75\r\n29\r\n34\r\n46\r\n20\r\n17\r\n66\r\n36\r\n81\r\n39\r\n27\r\n22\r\n24\r\n29\r\n39\r\n54\r\n39\r\n61\r\n54\r\n40\r\n41\r\n65\r\n45\r\n47\r\n62\r\n79\r\n67\r\n66\r\n50\r\n78\r\n43\r\n74\r\n40\r\n79\r\n67\r\n98\r\n64\r\n51\r\n82\r\n97\r\n98\r\n56\r\n67\r\n98\r\n131\r\n63\r\n57\r\n66\r\n67\r\n104\r\n75\r\n129\r\n128\r\n135\r\n65\r\n75\r\n148\r\n85\r\n132\r\n73\r\n108\r\n88\r\n89\r\n143\r\n96\r\n132\r\n94\r\n127\r\n89\r\n95\r\n146\r\n107\r\n140\r\n93\r\n121\r\n101\r\n90\r\n160\r\n120\r\n100\r\n112\r\n124\r\n100\r\n172\r\n150\r\n134\r\n128\r\n116\r\n162\r\n98\r\n171\r\n181\r\n88\r\n55\r\n26\r\n25\r\n77\r\n20\r\n35\r\n44\r\n37\r\n76\r\n39\r\n39\r\n36\r\n20\r\n15\r\n85\r\n83\r\n19\r\n21\r\n70\r\n6..."
    },
    {
      "input": "100 100 1 3 10000\r\n74 1 91 1\r\n47 1 61 2\r\n66 1 61 3\r\n53 1 37 4\r\n21 1 84 5\r\n55 1 32 6\r\n77 1 88 7\r\n28 1 89 8\r\n35 1 26 9\r\n69 1 69 10\r\n26 1 96 11\r\n58 1 4 12\r\n95 1 61 13\r\n81 1 36 14\r\n23 1 1 15\r\n80 1 16 16\r\n79 1 65 17\r\n39 1 47 18\r\n34 1 61 19\r\n80 1 4 20\r\n7 1 87 21\r\n98 1 65 22\r\n65 1 48 23\r\n78 1 64 24\r\n97 1 91 25\r\n85 1 72 26\r\n48 1 66 27\r\n64 1 35 28\r\n90 1 33 29\r\n10 1 29 30\r\n84 1 45 31\r\n98 1 59 32\r\n43 1 65 33\r\n71 1 47 34\r\n59 1 59 35\r\n30 1 59 36\r\n92 1 87 37\r\n79 1 66 38\r\n96 1 3 39\r\n100 1 37 40\r\n51 1 62 41\r\n36 1 1 42\r\n30...",
      "output": "17\r\n15\r\n7\r\n19\r\n67\r\n28\r\n17\r\n68\r\n17\r\n9\r\n80\r\n65\r\n46\r\n58\r\n36\r\n79\r\n30\r\n25\r\n45\r\n95\r\n100\r\n54\r\n39\r\n37\r\n30\r\n38\r\n44\r\n56\r\n85\r\n48\r\n69\r\n70\r\n54\r\n57\r\n34\r\n64\r\n41\r\n50\r\n131\r\n102\r\n51\r\n76\r\n54\r\n57\r\n127\r\n87\r\n68\r\n120\r\n122\r\n98\r\n75\r\n100\r\n99\r\n97\r\n85\r\n65\r\n131\r\n111\r\n70\r\n91\r\n92\r\n92\r\n69\r\n73\r\n137\r\n109\r\n101\r\n79\r\n73\r\n96\r\n84\r\n76\r\n75\r\n136\r\n99\r\n108\r\n169\r\n92\r\n108\r\n105\r\n100\r\n86\r\n117\r\n88\r\n93\r\n127\r\n161\r\n139\r\n95\r\n99\r\n92\r\n144\r\n108\r\n141\r\n131\r\n133\r\n128\r\n150\r\n107\r\n134\r\n35\r\n28\r\n14\r\n39\r\n57\r\n57\r\n6\r\n64\r\n59\r\n38\r\n26\r\n44\r\n30\r\n98\r\n17\r\n41\r\n27\r\n51\r\n42\r\n42\r\n46\r..."
    },
    {
      "input": "100 100 1 7 10000\r\n78 1 87 1\r\n49 1 99 2\r\n96 1 75 3\r\n75 1 82 4\r\n59 1 61 5\r\n22 1 55 6\r\n38 1 3 7\r\n8 1 8 8\r\n16 1 1 9\r\n49 1 30 10\r\n16 1 87 11\r\n3 1 57 12\r\n31 1 65 13\r\n61 1 22 14\r\n80 1 76 15\r\n73 1 54 16\r\n43 1 13 17\r\n74 1 30 18\r\n53 1 36 19\r\n34 1 33 20\r\n94 1 4 21\r\n38 1 90 22\r\n40 1 30 23\r\n21 1 67 24\r\n57 1 70 25\r\n48 1 15 26\r\n9 1 22 27\r\n52 1 77 28\r\n42 1 94 29\r\n19 1 57 30\r\n21 1 36 31\r\n43 1 74 32\r\n64 1 83 33\r\n2 1 70 34\r\n46 1 8 35\r\n25 1 65 36\r\n65 1 70 37\r\n80 1 30 38\r\n29 1 40 39\r\n100 1 48 40\r\n54 1 14 41\r\n58 1 28 42\r\n78 1 ...",
      "output": "9\r\n51\r\n23\r\n10\r\n6\r\n38\r\n41\r\n7\r\n23\r\n28\r\n81\r\n65\r\n46\r\n52\r\n18\r\n34\r\n46\r\n61\r\n35\r\n20\r\n110\r\n73\r\n32\r\n69\r\n37\r\n58\r\n39\r\n52\r\n80\r\n67\r\n45\r\n62\r\n51\r\n101\r\n72\r\n75\r\n41\r\n87\r\n49\r\n91\r\n80\r\n71\r\n73\r\n49\r\n45\r\n80\r\n118\r\n52\r\n88\r\n87\r\n99\r\n108\r\n93\r\n100\r\n76\r\n70\r\n116\r\n59\r\n77\r\n66\r\n65\r\n103\r\n82\r\n99\r\n74\r\n67\r\n74\r\n78\r\n130\r\n74\r\n106\r\n108\r\n87\r\n148\r\n104\r\n88\r\n102\r\n142\r\n101\r\n86\r\n116\r\n159\r\n134\r\n109\r\n84\r\n89\r\n94\r\n99\r\n135\r\n110\r\n166\r\n97\r\n118\r\n104\r\n172\r\n102\r\n148\r\n164\r\n154\r\n104\r\n7\r\n20\r\n4\r\n6\r\n85\r\n36\r\n43\r\n52\r\n46\r\n61\r\n49\r\n18\r\n31\r\n86\r\n79\r\n81\r\n18\r\n33\r\n58\r\n43\r\n59\r\n61\r..."
    },
    {
      "input": "100 100 1 10 10000\r\n82 1 25 1\r\n72 1 4 2\r\n5 1 9 3\r\n4 1 64 4\r\n59 1 23 5\r\n21 1 11 6\r\n60 1 50 7\r\n60 1 38 8\r\n26 1 26 9\r\n1 1 94 10\r\n62 1 25 11\r\n14 1 84 12\r\n1 1 23 13\r\n52 1 49 14\r\n7 1 75 15\r\n76 1 92 16\r\n35 1 40 17\r\n39 1 45 18\r\n45 1 58 19\r\n27 1 61 20\r\n54 1 45 21\r\n8 1 62 22\r\n16 1 54 23\r\n27 1 58 24\r\n56 1 46 25\r\n27 1 68 26\r\n22 1 47 27\r\n31 1 72 28\r\n24 1 48 29\r\n73 1 7 30\r\n31 1 69 31\r\n66 1 26 32\r\n61 1 42 33\r\n31 1 54 34\r\n9 1 50 35\r\n50 1 87 36\r\n14 1 59 37\r\n11 1 36 38\r\n24 1 52 39\r\n99 1 71 40\r\n18 1 35 41\r\n5 1 46 42\r\n10 1 72...",
      "output": "57\r\n69\r\n6\r\n63\r\n40\r\n15\r\n16\r\n29\r\n8\r\n102\r\n47\r\n81\r\n34\r\n16\r\n82\r\n31\r\n21\r\n23\r\n31\r\n53\r\n29\r\n75\r\n60\r\n54\r\n34\r\n66\r\n51\r\n68\r\n52\r\n95\r\n68\r\n71\r\n51\r\n56\r\n75\r\n72\r\n81\r\n62\r\n66\r\n67\r\n57\r\n82\r\n104\r\n47\r\n62\r\n108\r\n46\r\n130\r\n87\r\n137\r\n63\r\n90\r\n93\r\n66\r\n72\r\n66\r\n124\r\n83\r\n139\r\n81\r\n116\r\n70\r\n62\r\n82\r\n133\r\n133\r\n93\r\n71\r\n68\r\n76\r\n129\r\n81\r\n93\r\n141\r\n106\r\n107\r\n110\r\n106\r\n89\r\n131\r\n89\r\n174\r\n99\r\n141\r\n111\r\n156\r\n115\r\n133\r\n93\r\n129\r\n126\r\n112\r\n170\r\n111\r\n173\r\n113\r\n126\r\n97\r\n104\r\n144\r\n3\r\n2\r\n37\r\n48\r\n13\r\n61\r\n85\r\n81\r\n16\r\n65\r\n31\r\n46\r\n28\r\n14\r\n66\r\n42\r\n65\r\n93\r\n59\r\n50\r\n57..."
    },
    {
      "input": "100 100 17 20 10000\r\n46 1 92 1\r\n19 1 74 2\r\n40 1 44 3\r\n3 1 92 4\r\n49 1 90 5\r\n50 1 84 6\r\n98 1 12 7\r\n23 1 89 8\r\n96 1 86 9\r\n17 1 11 10\r\n3 1 98 11\r\n37 1 99 12\r\n75 1 86 13\r\n59 1 31 14\r\n58 1 65 15\r\n70 1 2 16\r\n41 1 94 17\r\n71 1 81 18\r\n86 1 59 19\r\n21 1 74 20\r\n89 1 47 21\r\n40 1 43 22\r\n52 1 41 23\r\n98 1 27 24\r\n92 1 5 25\r\n97 1 16 26\r\n75 1 17 27\r\n75 1 71 28\r\n61 1 54 29\r\n33 1 77 30\r\n66 1 100 31\r\n92 1 88 32\r\n71 1 68 33\r\n2 1 39 34\r\n37 1 33 35\r\n35 1 72 36\r\n72 1 13 37\r\n70 1 79 38\r\n5 1 78 39\r\n7 1 12 40\r\n72 1 45 41\r\n8 1 61 42\r\n71...",
      "output": "78\r\n86\r\n34\r\n118\r\n69\r\n61\r\n112\r\n91\r\n34\r\n29\r\n117\r\n83\r\n31\r\n47\r\n25\r\n85\r\n69\r\n27\r\n45\r\n72\r\n62\r\n24\r\n33\r\n94\r\n111\r\n106\r\n84\r\n31\r\n35\r\n73\r\n64\r\n35\r\n35\r\n70\r\n38\r\n72\r\n95\r\n46\r\n111\r\n44\r\n67\r\n94\r\n71\r\n107\r\n64\r\n69\r\n91\r\n81\r\n56\r\n71\r\n90\r\n136\r\n106\r\n139\r\n72\r\n97\r\n100\r\n123\r\n125\r\n111\r\n121\r\n71\r\n76\r\n102\r\n84\r\n67\r\n73\r\n116\r\n87\r\n72\r\n76\r\n119\r\n80\r\n85\r\n79\r\n114\r\n115\r\n164\r\n84\r\n99\r\n146\r\n120\r\n92\r\n107\r\n94\r\n127\r\n89\r\n142\r\n157\r\n132\r\n98\r\n101\r\n107\r\n98\r\n116\r\n149\r\n97\r\n106\r\n115\r\n135\r\n35\r\n59\r\n54\r\n39\r\n88\r\n47\r\n58\r\n103\r\n61\r\n34\r\n104\r\n39\r\n25\r\n57\r\n39\r\n25\r\n77\r\n20\r\n56..."
    },
    {
      "input": "100 99 2 99 9801\r\n92 1 82 1\r\n41 1 73 2\r\n44 1 74 3\r\n42 1 78 4\r\n82 1 47 5\r\n48 1 52 6\r\n84 1 47 7\r\n67 1 44 8\r\n94 1 73 9\r\n93 1 60 10\r\n98 1 16 11\r\n70 1 3 12\r\n96 1 98 13\r\n96 1 56 14\r\n99 1 20 15\r\n25 1 44 16\r\n57 1 22 17\r\n48 1 48 18\r\n55 1 76 19\r\n3 1 53 20\r\n55 1 38 21\r\n8 1 82 22\r\n1 1 29 23\r\n15 1 32 24\r\n47 1 81 25\r\n26 1 78 26\r\n37 1 2 27\r\n73 1 60 28\r\n49 1 80 29\r\n23 1 53 30\r\n24 1 16 31\r\n63 1 9 32\r\n87 1 4 33\r\n71 1 48 34\r\n38 1 45 35\r\n32 1 45 36\r\n85 1 96 37\r\n4 1 3 38\r\n82 1 50 39\r\n55 1 53 40\r\n33 1 11 41\r\n35 1 44 42\r\n12 1 20...",
      "output": "12\r\n33\r\n32\r\n39\r\n39\r\n9\r\n43\r\n30\r\n29\r\n42\r\n92\r\n78\r\n14\r\n53\r\n93\r\n34\r\n51\r\n17\r\n39\r\n69\r\n37\r\n95\r\n50\r\n40\r\n58\r\n77\r\n61\r\n40\r\n59\r\n59\r\n38\r\n85\r\n115\r\n56\r\n41\r\n48\r\n47\r\n38\r\n70\r\n41\r\n62\r\n50\r\n50\r\n61\r\n54\r\n124\r\n67\r\n54\r\n89\r\n73\r\n129\r\n90\r\n98\r\n65\r\n54\r\n58\r\n77\r\n89\r\n73\r\n74\r\n69\r\n109\r\n81\r\n119\r\n142\r\n87\r\n97\r\n102\r\n128\r\n96\r\n120\r\n161\r\n95\r\n77\r\n77\r\n76\r\n90\r\n121\r\n149\r\n136\r\n80\r\n146\r\n139\r\n129\r\n91\r\n97\r\n92\r\n88\r\n100\r\n113\r\n95\r\n107\r\n176\r\n123\r\n118\r\n134\r\n132\r\n100\r\n138\r\n21\r\n8\r\n12\r\n38\r\n16\r\n60\r\n5\r\n15\r\n30\r\n10\r\n20\r\n17\r\n41\r\n88\r\n75\r\n18\r\n25\r\n42\r\n22\r\n50\r\n61\r\n33\r\n28\r\n..."
    },
    {
      "input": "100 99 2 30 9801\r\n79 1 89 1\r\n73 1 50 2\r\n94 1 46 3\r\n32 1 60 4\r\n11 1 99 5\r\n25 1 38 6\r\n46 1 45 7\r\n82 1 38 8\r\n6 1 62 9\r\n15 1 55 10\r\n100 1 16 11\r\n87 1 55 12\r\n14 1 93 13\r\n67 1 98 14\r\n61 1 29 15\r\n72 1 97 16\r\n3 1 23 17\r\n1 1 46 18\r\n94 1 67 19\r\n67 1 37 20\r\n99 1 21 21\r\n95 1 58 22\r\n40 1 71 23\r\n72 1 4 24\r\n43 1 71 25\r\n50 1 4 26\r\n20 1 81 27\r\n68 1 83 28\r\n11 1 98 29\r\n87 1 54 30\r\n11 1 19 31\r\n61 1 65 32\r\n57 1 14 33\r\n19 1 53 34\r\n59 1 64 35\r\n51 1 34 36\r\n77 1 42 37\r\n50 1 56 38\r\n23 1 33 39\r\n95 1 78 40\r\n1 1 56 41\r\n47 1 90 42\r\n50 ...",
      "output": "12\r\n24\r\n50\r\n31\r\n92\r\n18\r\n7\r\n51\r\n64\r\n49\r\n94\r\n43\r\n91\r\n44\r\n46\r\n40\r\n36\r\n62\r\n45\r\n49\r\n98\r\n58\r\n53\r\n91\r\n52\r\n71\r\n87\r\n42\r\n115\r\n62\r\n38\r\n35\r\n75\r\n67\r\n39\r\n52\r\n71\r\n43\r\n48\r\n56\r\n95\r\n84\r\n78\r\n51\r\n86\r\n71\r\n110\r\n115\r\n107\r\n89\r\n76\r\n83\r\n85\r\n74\r\n84\r\n107\r\n69\r\n135\r\n84\r\n85\r\n81\r\n115\r\n78\r\n85\r\n74\r\n72\r\n149\r\n68\r\n89\r\n100\r\n111\r\n92\r\n95\r\n119\r\n141\r\n81\r\n85\r\n142\r\n86\r\n104\r\n113\r\n97\r\n140\r\n86\r\n124\r\n105\r\n119\r\n90\r\n106\r\n120\r\n99\r\n91\r\n122\r\n95\r\n101\r\n130\r\n145\r\n187\r\n182\r\n42\r\n72\r\n20\r\n22\r\n33\r\n64\r\n51\r\n23\r\n27\r\n42\r\n29\r\n34\r\n47\r\n32\r\n46\r\n23\r\n95\r\n30\r\n38\r\n56\r\n26\r\n38\r\n7..."
    },
    {
      "input": "100 99 2 31 9801\r\n3 1 66 1\r\n18 1 30 2\r\n55 1 32 3\r\n20 1 3 4\r\n66 1 91 5\r\n65 1 25 6\r\n40 1 77 7\r\n9 1 49 8\r\n21 1 5 9\r\n33 1 98 10\r\n40 1 9 11\r\n8 1 53 12\r\n71 1 12 13\r\n88 1 70 14\r\n81 1 75 15\r\n98 1 42 16\r\n94 1 62 17\r\n14 1 50 18\r\n27 1 17 19\r\n8 1 4 20\r\n100 1 7 21\r\n76 1 13 22\r\n29 1 64 23\r\n83 1 36 24\r\n65 1 73 25\r\n68 1 37 26\r\n13 1 24 27\r\n64 1 68 28\r\n98 1 8 29\r\n38 1 68 30\r\n19 1 60 31\r\n96 1 63 32\r\n88 1 37 33\r\n96 1 52 34\r\n58 1 4 35\r\n99 1 35 36\r\n92 1 35 37\r\n26 1 74 38\r\n79 1 87 39\r\n48 1 4 40\r\n48 1 13 41\r\n73 1 44 42\r\n85 1 94 4...",
      "output": "65\r\n13\r\n25\r\n20\r\n29\r\n45\r\n43\r\n47\r\n24\r\n74\r\n41\r\n56\r\n71\r\n31\r\n20\r\n71\r\n48\r\n53\r\n28\r\n23\r\n113\r\n84\r\n57\r\n70\r\n32\r\n56\r\n37\r\n31\r\n118\r\n59\r\n71\r\n64\r\n83\r\n77\r\n88\r\n99\r\n93\r\n85\r\n46\r\n83\r\n75\r\n70\r\n51\r\n67\r\n47\r\n83\r\n68\r\n92\r\n83\r\n57\r\n75\r\n83\r\n85\r\n139\r\n82\r\n104\r\n67\r\n86\r\n89\r\n155\r\n102\r\n124\r\n65\r\n148\r\n86\r\n135\r\n114\r\n85\r\n87\r\n158\r\n93\r\n163\r\n124\r\n106\r\n136\r\n154\r\n108\r\n140\r\n167\r\n148\r\n94\r\n86\r\n103\r\n158\r\n144\r\n147\r\n170\r\n132\r\n89\r\n103\r\n91\r\n126\r\n176\r\n110\r\n170\r\n123\r\n140\r\n155\r\n147\r\n73\r\n29\r\n12\r\n13\r\n58\r\n44\r\n32\r\n48\r\n47\r\n48\r\n31\r\n41\r\n17\r\n35\r\n68\r\n18\r\n54\r\n70\r\n30\r\n44\r\n..."
    },
    {
      "input": "2 100 34 74 10000\r\n2 1 2 1\r\n2 1 2 2\r\n2 1 2 3\r\n2 1 2 4\r\n1 1 1 5\r\n1 1 1 6\r\n1 1 1 7\r\n2 1 2 8\r\n2 1 2 9\r\n1 1 1 10\r\n1 1 1 11\r\n2 1 2 12\r\n1 1 1 13\r\n2 1 2 14\r\n2 1 2 15\r\n1 1 1 16\r\n2 1 2 17\r\n1 1 1 18\r\n1 1 1 19\r\n1 1 1 20\r\n1 1 1 21\r\n2 1 2 22\r\n2 1 2 23\r\n2 1 2 24\r\n1 1 1 25\r\n1 1 1 26\r\n1 1 1 27\r\n1 1 1 28\r\n2 1 2 29\r\n1 1 1 30\r\n1 1 1 31\r\n2 1 2 32\r\n2 1 2 33\r\n2 1 2 34\r\n1 1 1 35\r\n1 1 1 36\r\n2 1 2 37\r\n1 1 1 38\r\n2 1 2 39\r\n1 1 1 40\r\n1 1 1 41\r\n1 1 1 42\r\n1 1 1 43\r\n1 1 1 44\r\n2 1 2 45\r\n1 1 1 46\r\n1 1 1 47\r\n1 1 1 48\r\n2 1 2 49\r\n2 1 2 50\r\n1...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n20\r\n21\r\n22\r\n23\r\n24\r\n25\r\n26\r\n27\r\n28\r\n29\r\n30\r\n31\r\n32\r\n33\r\n34\r\n35\r\n36\r\n37\r\n38\r\n39\r\n40\r\n41\r\n42\r\n43\r\n44\r\n45\r\n46\r\n47\r\n48\r\n49\r\n50\r\n51\r\n52\r\n53\r\n54\r\n55\r\n56\r\n57\r\n58\r\n59\r\n60\r\n61\r\n62\r\n63\r\n64\r\n65\r\n66\r\n67\r\n68\r\n69\r\n70\r\n71\r\n72\r\n73\r\n74\r\n75\r\n76\r\n77\r\n78\r\n79\r\n80\r\n81\r\n82\r\n83\r\n84\r\n85\r\n86\r\n87\r\n88\r\n89\r\n90\r\n91\r\n92\r\n93\r\n94\r\n95\r\n96\r\n97\r\n98\r\n99\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n20\r\n21\r\n22\r\n23\r\n24\r\n25\r\n26\r\n27\r\n28\r\n29\r\n30\r\n31\r\n..."
    },
    {
      "input": "2 99 25 27 9801\r\n2 1 2 1\r\n1 1 1 2\r\n1 1 1 3\r\n1 1 1 4\r\n1 1 1 5\r\n2 1 2 6\r\n2 1 2 7\r\n2 1 2 8\r\n2 1 2 9\r\n1 1 1 10\r\n1 1 1 11\r\n2 1 2 12\r\n2 1 2 13\r\n1 1 1 14\r\n2 1 2 15\r\n1 1 1 16\r\n1 1 1 17\r\n1 1 1 18\r\n1 1 1 19\r\n1 1 1 20\r\n1 1 1 21\r\n1 1 1 22\r\n2 1 2 23\r\n1 1 1 24\r\n1 1 1 25\r\n2 1 2 26\r\n2 1 2 27\r\n1 1 1 28\r\n1 1 1 29\r\n1 1 1 30\r\n2 1 2 31\r\n1 1 1 32\r\n1 1 1 33\r\n1 1 1 34\r\n1 1 1 35\r\n1 1 1 36\r\n2 1 2 37\r\n2 1 2 38\r\n2 1 2 39\r\n1 1 1 40\r\n2 1 2 41\r\n1 1 1 42\r\n2 1 2 43\r\n2 1 2 44\r\n1 1 1 45\r\n1 1 1 46\r\n1 1 1 47\r\n2 1 2 48\r\n2 1 2 49\r\n1 1 1 50\r\n1 1...",
      "output": "0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n20\r\n21\r\n22\r\n23\r\n24\r\n25\r\n26\r\n27\r\n28\r\n29\r\n30\r\n31\r\n32\r\n33\r\n34\r\n35\r\n36\r\n37\r\n38\r\n39\r\n40\r\n41\r\n42\r\n43\r\n44\r\n45\r\n46\r\n47\r\n48\r\n49\r\n50\r\n51\r\n52\r\n53\r\n54\r\n55\r\n56\r\n57\r\n58\r\n59\r\n60\r\n61\r\n62\r\n63\r\n64\r\n65\r\n66\r\n67\r\n68\r\n69\r\n70\r\n71\r\n72\r\n73\r\n74\r\n75\r\n76\r\n77\r\n78\r\n79\r\n80\r\n81\r\n82\r\n83\r\n84\r\n85\r\n86\r\n87\r\n88\r\n89\r\n90\r\n91\r\n92\r\n93\r\n94\r\n95\r\n96\r\n97\r\n98\r\n1\r\n0\r\n1\r\n2\r\n3\r\n4\r\n5\r\n6\r\n7\r\n8\r\n9\r\n10\r\n11\r\n12\r\n13\r\n14\r\n15\r\n16\r\n17\r\n18\r\n19\r\n20\r\n21\r\n22\r\n23\r\n24\r\n25\r\n26\r\n27\r\n28\r\n29\r\n30\r\n31\r\n32\r\n..."
    },
    {
      "input": "100000000 100000000 2 3 10000\r\n2466157 88773932 26281360 99782414\r\n18378798 19984585 22799370 74943050\r\n54660405 27520230 70314965 36864965\r\n41327399 11303293 98375878 60295933\r\n10182700 51697836 47934073 52868817\r\n9122675 82394677 77221581 2188550\r\n54927532 56890365 99603046 42305731\r\n69351308 75297168 49445674 73138453\r\n54118221 38067099 98346948 83504492\r\n79972395 33756529 52159269 5059100\r\n59076072 41143176 20542973 48338397\r\n86202440 92901881 5126726 70866508\r\n89874582 28701443 25425594 66833256\r\n4982...",
      "output": "212371543\r\n99348201\r\n80039749\r\n128647699\r\n142318020\r\n152682127\r\n143871604\r\n168341249\r\n165800312\r\n66628749\r\n128014666\r\n244844097\r\n159983681\r\n141296477\r\n141842775\r\n153138339\r\n102096129\r\n129543767\r\n90345770\r\n140397562\r\n122140404\r\n138539209\r\n127125151\r\n111198226\r\n128812653\r\n206514575\r\n124722116\r\n143553341\r\n178669952\r\n91346675\r\n124042728\r\n144677349\r\n180698908\r\n188071429\r\n33530621\r\n120402228\r\n165154482\r\n206720467\r\n59044760\r\n208184519\r\n188941831\r\n81857851\r\n170924594\r\n110250091\r\n64213686\r\n166227748\r\n169243667\r\n134..."
    },
    {
      "input": "100000000 100000000 2 100000000 10000\r\n2612471 48868162 29162850 57692091\r\n31688767 62108610 77923010 74959754\r\n57830095 15800895 92114075 93061963\r\n62035859 76169684 7612540 87883657\r\n55511003 83853726 73866134 72765460\r\n54005466 12336701 37168447 28894079\r\n41264938 37703000 11542387 65303713\r\n66391367 17156118 54008910 90201877\r\n58409999 7098277 61550995 91167674\r\n35190088 8520630 81755944 8804147\r\n53620506 77917183 28972696 3791463\r\n54388113 53543352 4298639 71716098\r\n40315164 1609247 58569570 34895603\r...",
      "output": "35374308\r\n59085387\r\n111545048\r\n66137292\r\n29443397\r\n33394397\r\n57323264\r\n85428216\r\n87210393\r\n46849373\r\n98773530\r\n68262220\r\n51540762\r\n74951572\r\n42090797\r\n84522342\r\n34026933\r\n79747220\r\n63130058\r\n97205595\r\n116488446\r\n65779404\r\n54405272\r\n68136749\r\n16633031\r\n116544182\r\n33523678\r\n52026328\r\n46772702\r\n98572591\r\n99445036\r\n90024612\r\n87758628\r\n51115776\r\n87393362\r\n37246346\r\n94676159\r\n79509819\r\n79267664\r\n35776782\r\n97140857\r\n70740401\r\n59539153\r\n22521606\r\n16131555\r\n37787490\r\n45639187\r\n133194054\r\n59459965\r\n91949769\r\n1741791..."
    },
    {
      "input": "100000000 100000000 1 100000000 10000\r\n59428483 27934007 46858668 83431652\r\n10320511 64500008 3353473 52989431\r\n75349474 87328981 92642325 24663945\r\n17738914 29105936 87464762 72776148\r\n88412427 51474461 3555926 59671239\r\n28356413 93655093 90092769 61374853\r\n71754668 88360708 44566250 49468900\r\n73796766 46288684 34811539 64614639\r\n10844081 50657984 67965585 78969189\r\n25655634 20362441 85162157 92490039\r\n56296262 4450757 72444229 79045645\r\n7169061 79452963 72024011 88755906\r\n98955226 16043464 22522949 76515...",
      "output": "68067460\r\n18477615\r\n79957887\r\n113396060\r\n93053279\r\n94016596\r\n66080226\r\n57311182\r\n85432709\r\n131634121\r\n90742855\r\n74157893\r\n136904369\r\n96244302\r\n22163554\r\n59739732\r\n77058599\r\n99869304\r\n143699311\r\n50855178\r\n72962270\r\n68488054\r\n64973935\r\n65622871\r\n41164199\r\n40635407\r\n28222110\r\n35732879\r\n64329476\r\n81494946\r\n89102220\r\n6865400\r\n15748160\r\n154310563\r\n49880677\r\n40846414\r\n24774673\r\n80332305\r\n14099424\r\n13929118\r\n72622321\r\n110481289\r\n109487514\r\n81364156\r\n60946271\r\n8222870\r\n63447876\r\n9305867\r\n94589931\r\n26735692\r\n5405154..."
    },
    {
      "input": "100000000 100000000 1 99999999 10000\r\n43127935 71836794 54786128 56441208\r\n32890601 53926432 65107984 44963397\r\n37309646 82487199 13188488 28931586\r\n70785104 82421202 42534008 60602037\r\n41192040 86548363 22708401 53093274\r\n1527905 55586061 30207640 83783583\r\n20122971 6506643 68752807 16875751\r\n73703625 80670920 16305388 39394632\r\n59761651 46341198 65554569 60725453\r\n72658293 72491063 78089778 83253044\r\n70219966 50830223 72979890 81964400\r\n95163538 9176016 36843622 1241128\r\n59667337 41640811 20546496 646771...",
      "output": "27053779\r\n41180418\r\n77676771\r\n50070261\r\n51938728\r\n56877257\r\n58998944\r\n98674525\r\n20177173\r\n16193466\r\n33894101\r\n66254804\r\n62157205\r\n44817125\r\n110674780\r\n71098713\r\n77502663\r\n59396512\r\n59916461\r\n57422226\r\n41739902\r\n78948893\r\n29548703\r\n2980748\r\n77917193\r\n35020050\r\n64108504\r\n44604042\r\n83500718\r\n54579431\r\n52300185\r\n29041929\r\n115405718\r\n60564917\r\n133983917\r\n40179808\r\n80111035\r\n78543166\r\n60206014\r\n91810687\r\n107449094\r\n102213052\r\n87827389\r\n124672745\r\n33372295\r\n43388721\r\n43895290\r\n28906378\r\n66909225\r\n99349348\r\n380617..."
    },
    {
      "input": "100000000 100000000 72143325 79143325 10000\r\n65404874 37264473 6587117 43155487\r\n63158852 69552039 69491412 52365786\r\n77375670 29245756 18720574 39527610\r\n61516382 71045285 70299468 80641022\r\n75691106 62751988 36418118 15088810\r\n49624394 60847164 89112085 94200835\r\n11803010 6305048 37465288 4923415\r\n55888346 33957413 43692559 54515763\r\n58596613 71559043 40247747 92714346\r\n91976989 18169688 39387484 37254421\r\n50828061 60986189 75759993 38684494\r\n20102246 75862799 56739164 2125171\r\n86087739 234191 75619179 3...",
      "output": "122684447\r\n28701385\r\n134168380\r\n18378823\r\n105718840\r\n72841362\r\n158720465\r\n68009261\r\n39504169\r\n141452046\r\n69547899\r\n110374546\r\n123693842\r\n78447872\r\n68528817\r\n153318540\r\n124156214\r\n87425787\r\n92797685\r\n72365403\r\n111007521\r\n75728396\r\n52151747\r\n32231228\r\n53580670\r\n58673496\r\n46653507\r\n107528489\r\n104647803\r\n123985683\r\n70558360\r\n158328711\r\n84683699\r\n81020954\r\n92084108\r\n108741258\r\n143801876\r\n84257131\r\n63718686\r\n87780395\r\n33100492\r\n160012453\r\n75297591\r\n140302148\r\n147588301\r\n108810953\r\n36900180\r\n192201204\r\n50540081\r\n..."
    },
    {
      "input": "100000000 100000000 79143325 79143327 10000\r\n74006099 28600551 24880332 68336589\r\n69329301 42934730 16307562 83475068\r\n46167121 21314785 56843793 59620581\r\n41613540 70252092 59230571 13546098\r\n96139233 56045887 56357011 54406687\r\n83908495 58114850 10861467 89520384\r\n29113449 27916144 92325640 57036985\r\n10798748 8319880 32159825 42608900\r\n54301068 29037600 5582179 17525039\r\n15921999 16692413 85656864 40132507\r\n60042800 50303035 55023067 86876222\r\n15385390 30501451 53879005 25765922\r\n15936890 73650928 524006...",
      "output": "110475277\r\n93562077\r\n88027956\r\n92105491\r\n87616298\r\n104452562\r\n136545712\r\n128718947\r\n160442900\r\n171196595\r\n41592920\r\n140512892\r\n111909584\r\n45630830\r\n79159446\r\n141538723\r\n69238290\r\n110921258\r\n201317728\r\n121724629\r\n77124655\r\n98153076\r\n81512257\r\n107979625\r\n46639731\r\n123745712\r\n28339034\r\n99021661\r\n162195758\r\n112893712\r\n64741466\r\n90097268\r\n102166767\r\n49023690\r\n103919258\r\n79750219\r\n166638151\r\n159433921\r\n85828153\r\n158933301\r\n94744963\r\n24816480\r\n136225200\r\n156700083\r\n132889345\r\n87499441\r\n114018841\r\n185695748\r\n11508..."
    },
    {
      "input": "100000000 100000000 77777777 77777778 10000\r\n37934353 12121019 75776795 77901751\r\n43532657 50052382 95009542 39466151\r\n93939571 95842394 92588898 1842331\r\n88953647 69587046 33904331 90323931\r\n10440164 86922237 67663426 95850934\r\n13845876 55574814 95496107 49710076\r\n26075621 33554060 64973901 39425922\r\n91256033 58319182 71186517 53585314\r\n35708214 59146288 94643283 92139704\r\n91937624 89318209 35926202 93487526\r\n41387994 50982228 55923300 32069968\r\n49997561 99175295 14890253 27095329\r\n74651153 41301150 33211...",
      "output": "103623174\r\n117513906\r\n95350736\r\n75786201\r\n84440877\r\n131920895\r\n121473852\r\n63720574\r\n91928485\r\n83261601\r\n87038664\r\n107187274\r\n128037373\r\n164003644\r\n63448662\r\n114700932\r\n27760449\r\n108346202\r\n97119011\r\n120674382\r\n109908677\r\n50590975\r\n88089327\r\n59420471\r\n71954301\r\n162052960\r\n48920938\r\n114534344\r\n75051112\r\n89882091\r\n14868217\r\n86016277\r\n104043079\r\n76871369\r\n97279171\r\n28884511\r\n146454587\r\n138188366\r\n126954281\r\n93563270\r\n140421514\r\n90543480\r\n91723476\r\n95218549\r\n87791724\r\n132612266\r\n102146488\r\n83970222\r\n118399153\r\n..."
    },
    {
      "input": "10 2 1 1 400\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 10 1\r\n1 1 10 2\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 4 1\r\n1 2 4 2\r\n1 2 5 1\r\n1 2 5 2\r\n1 2 6 1\r\n1 2 6 2\r\n1 2 7 1\r\n1 2 7 2\r\n1 2 8 1\r\n1 2 8 2\r\n1 2 9 1\r\n1 2 9 2\r\n1 2 10 1\r\n1 2 10 2\r\n2 1 1 1\r\n2 1 1 2\r\n2 1 2 1\r\n2 1 2 2\r\n2 1 3 1\r\n2 1 3 2\r\n2 1 4 1\r\n2 1 4 2\r\n2 1 5 1\r\n2 1 5 2\r\n2 1 6 1\r\n2 1 6 2\r\n2 1 7 1\r\n2 1 7 2\r\n2 1 8 1...",
      "output": "0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n9\r\n10\r\n1\r\n0\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n9\r\n10\r\n10\r\n11\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n2\r\n3\r\n1\r\n0\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n9\r\n10\r\n2\r\n3\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n3\r\n4\r\n2\r\n3\r\n1\r\n0\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n3\r\n4\r\n2\r\n3\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n4\r\n5\r\n3\r\n4\r\n2\r\n3\r\n1\r\n0\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n4\r\n5\r\n3\r\n4\r\n2\r\n3\r\n1\r\n2\r\n0\r..."
    },
    {
      "input": "10 2 2 2 400\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 10 1\r\n1 1 10 2\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 4 1\r\n1 2 4 2\r\n1 2 5 1\r\n1 2 5 2\r\n1 2 6 1\r\n1 2 6 2\r\n1 2 7 1\r\n1 2 7 2\r\n1 2 8 1\r\n1 2 8 2\r\n1 2 9 1\r\n1 2 9 2\r\n1 2 10 1\r\n1 2 10 2\r\n2 1 1 1\r\n2 1 1 2\r\n2 1 2 1\r\n2 1 2 2\r\n2 1 3 1\r\n2 1 3 2\r\n2 1 4 1\r\n2 1 4 2\r\n2 1 5 1\r\n2 1 5 2\r\n2 1 6 1\r\n2 1 6 2\r\n2 1 7 1\r\n2 1 7 2\r\n2 1 8 1...",
      "output": "0\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n10\r\n9\r\n11\r\n10\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n10\r\n9\r\n3\r\n2\r\n0\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n10\r\n9\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n4\r\n3\r\n3\r\n2\r\n0\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n3\r\n2\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n5\r\n4\r\n4\r\n3\r\n3\r\n2\r\n0\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n4\r\n3\r\n3\r\n2\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n6\r\n5\r\n5\r\n4\r\n4\r\n3\r\n3\r\n2\r\n0\r..."
    },
    {
      "input": "10 2 1 2 400\r\n1 1 1 1\r\n1 1 1 2\r\n1 1 2 1\r\n1 1 2 2\r\n1 1 3 1\r\n1 1 3 2\r\n1 1 4 1\r\n1 1 4 2\r\n1 1 5 1\r\n1 1 5 2\r\n1 1 6 1\r\n1 1 6 2\r\n1 1 7 1\r\n1 1 7 2\r\n1 1 8 1\r\n1 1 8 2\r\n1 1 9 1\r\n1 1 9 2\r\n1 1 10 1\r\n1 1 10 2\r\n1 2 1 1\r\n1 2 1 2\r\n1 2 2 1\r\n1 2 2 2\r\n1 2 3 1\r\n1 2 3 2\r\n1 2 4 1\r\n1 2 4 2\r\n1 2 5 1\r\n1 2 5 2\r\n1 2 6 1\r\n1 2 6 2\r\n1 2 7 1\r\n1 2 7 2\r\n1 2 8 1\r\n1 2 8 2\r\n1 2 9 1\r\n1 2 9 2\r\n1 2 10 1\r\n1 2 10 2\r\n2 1 1 1\r\n2 1 1 2\r\n2 1 2 1\r\n2 1 2 2\r\n2 1 3 1\r\n2 1 3 2\r\n2 1 4 1\r\n2 1 4 2\r\n2 1 5 1\r\n2 1 5 2\r\n2 1 6 1\r\n2 1 6 2\r\n2 1 7 1\r\n2 1 7 2\r\n2 1 8 1...",
      "output": "0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n9\r\n10\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n10\r\n9\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n8\r\n9\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n9\r\n8\r\n2\r\n3\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n7\r\n8\r\n3\r\n2\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n8\r\n7\r\n3\r\n4\r\n2\r\n3\r\n1\r\n2\r\n0\r\n1\r\n1\r\n2\r\n2\r\n3\r\n3\r\n4\r\n4\r\n5\r\n5\r\n6\r\n6\r\n7\r\n4\r\n3\r\n3\r\n2\r\n2\r\n1\r\n1\r\n0\r\n2\r\n1\r\n3\r\n2\r\n4\r\n3\r\n5\r\n4\r\n6\r\n5\r\n7\r\n6\r\n4\r\n5\r\n3\r\n4\r\n2\r\n3\r\n1\r\n2\r\n0\r\n1\r..."
    },
    {
      "input": "100000000 100000000 100000000 100000000 1\r\n100000000 100000000 100000000 1",
      "output": "99999999"
    }
  ],
  "reference_solution": {
    "submission_id": 330513289,
    "submission_url": "https://codeforces.com/contest/1020/submission/330513289",
    "author_handle": "YasSaMaher",
    "author_rating": null,
    "language": "C++23 (GCC 14-64, msys2)",
    "code": "#include <iostream>\n#include <cmath>\n#include <iomanip>\n#include <algorithm>\n#include <string>\n#include <vector>\n#include <queue>\n#include <deque>\n#include <set>\n#include <unordered_set>\n#include <stack>\n#include <map>\n#include <unordered_map>\n   using namespace std;\n    void fast()\n{\n    ios_base::sync_with_stdio(0);\n    cin.tie(0);\n    cout.tie(0);\n}\n  long long gcd(long long a, long long b)\n{\n    while (b != 0)\n    {\n        long long temp = b;\n        b = a % b;\n        a = temp;\n    }\n    return a;\n}\n  long long lcm(long long a, long long b)\n{\n    return (a / gcd(a, b)) * b;\n}\n     int main()\n{\n   fast();\n   /*\n   int t;\n   cin >> t;\n   while(t--){\n    }\n   */\n   int n,h,a,b,k;\n   cin>>n>>h>>a>>b>>k;\n   while(k--){\n    int ta,fa,tb,fb;\n    cin>>ta>>fa>>tb>>fb;\n    if(ta==tb){cout<<abs(fa-fb)<<'\\n'; continue;}\n    if(fa>=a && fa<=b){cout<<abs(fa-fb)+abs(ta-tb)<<'\\n';}\n    else if(fa<a){cout<<(a-fa)+abs(a-fb)+abs(ta-tb)<<'\\n';}\n    else if(fa>b){cout<<(fa-b)+abs(b-fb)+abs(ta-tb)<<'\\n';}\n   }\n    return 0;\n}"
  },
  "verified_pseudocode": "// Time Complexity: O(K) for K queries, as each query takes O(1) time.\n// Space Complexity: O(1).\n\nFUNCTION SOLVE():\n  // Read building parameters\n  READ n, h, a, b, k\n\n  // Process each query\n  FOR i FROM 1 TO k:\n    // Read query specific locations\n    READ ta, fa, tb, fb\n\n    // Case 1: Start and end locations are in the same tower.\n    // Only vertical movement is needed.\n    IF ta == tb THEN\n      PRINT ABS(fa - fb)\n    ELSE\n      // Case 2: Start and end locations are in different towers.\n      // Movement involves vertical travel in tower 'ta' to a passage floor, \n      // horizontal travel between towers 'ta' and 'tb' on that passage floor,\n      // and then vertical travel in tower 'tb' to floor 'fb'.\n\n      // Calculate the vertical cost to reach an optimal passage floor from 'fa' in tower 'ta'.\n      // The optimal passage floor (x_cross_floor) is the one within [a, b] that is closest to 'fa'.\n      // If 'fa' is already within [a, b], 'x_cross_floor' can be 'fa' itself (cost 0).\n      // If 'fa' is below 'a', 'x_cross_floor' must be 'a'.\n      // If 'fa' is above 'b', 'x_cross_floor' must be 'b'.\n\n      cost_vertical_from_fa = 0\n      x_cross_floor = 0\n\n      IF fa < a THEN\n        cost_vertical_from_fa = a - fa\n        x_cross_floor = a\n      ELSE IF fa > b THEN\n        cost_vertical_from_fa = fa - b\n        x_cross_floor = b\n      ELSE // a <= fa <= b\n        cost_vertical_from_fa = 0\n        x_cross_floor = fa\n      END IF\n\n      // Calculate horizontal travel cost between towers.\n      cost_horizontal = ABS(ta - tb)\n      \n      // Calculate vertical travel cost from the chosen passage floor to 'fb' in tower 'tb'.\n      cost_vertical_to_fb = ABS(x_cross_floor - fb)\n\n      // Total time is the sum of these three costs.\n      total_time = cost_vertical_from_fa + cost_horizontal + cost_vertical_to_fb\n      PRINT total_time\n    END IF\n  END FOR\nEND FUNCTION\n",
  "verified_solution_code": "#include <bits/stdc++.h>\nusing namespace std;\n\nvoid solve() {\n    long long n, h, a, b, k;\n    cin >> n >> h >> a >> b >> k;\n\n    for (int i = 0; i < k; i++) {\n        long long ta, fa, tb, fb;\n        cin >> ta >> fa >> tb >> fb;\n\n        if (ta == tb) {\n            cout << abs(fa - fb) << endl;\n        } else {\n            long long cost_vertical_from_fa = 0;\n            long long x_cross_floor = 0;\n\n            if (fa < a) {\n                cost_vertical_from_fa = a - fa;\n                x_cross_floor = a;\n            } else if (fa > b) {\n                cost_vertical_from_fa = fa - b;\n                x_cross_floor = b;\n            } else {\n                cost_vertical_from_fa = 0;\n                x_cross_floor = fa;\n            }\n\n            long long cost_horizontal = abs(ta - tb);\n            long long cost_vertical_to_fb = abs(x_cross_floor - fb);\n\n            long long total_time = cost_vertical_from_fa + cost_horizontal + cost_vertical_to_fb;\n            cout << total_time << endl;\n        }\n    }\n}\n\nint main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n\n    solve();\n\n    return 0;\n}",
  "code_quality_analysis": {
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {
      "oracle_0": {
        "rating": "Excellent",
        "justification": "The solution implements the optimal O(1) algorithm per query. It correctly identifies two main cases: travel within the same tower and travel between different towers. For travel between different towers, it correctly calculates the minimum vertical travel to reach an allowed passage floor (a or b), the horizontal travel between towers, and then the final vertical travel to the destination floor. The logic is clean, concise, and correctly handles all described edge cases and constraints (e.g., large N, H)."
      }
    }
  }
}
```

## Problem: 1020B

```json
{
  "problem_id": "1020B",
  "problem_url": "https://codeforces.com/problemset/problem/1020/B",
  "problem_metadata": {
    "name": "Badge",
    "tags": [
      "brute force",
      "dfs and similar",
      "graphs"
    ],
    "time_limit_ms": 1000,
    "memory_limit_kb": 262144,
    "pretest_source": "internal_api"
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div><p>In Summer Informatics School, if a student doesn't behave well, teachers make a hole in his badge. And today one of the teachers caught a group of $$$n$$$ students doing yet another trick. </p><p>Let's assume that all these students are numbered from $$$1$$$ to $$$n$$$. The teacher came to student $$$a$$$ and put a hole in his badge. The student, however, claimed that the main culprit is some other student $$$p_a$$$.</p><p>After that, the teacher came to student $$$p_a$$$ and made a hole in his badge as well. The student in reply said that the main culprit was student $$$p_{p_a}$$$.</p><p>This process went on for a while, but, since the number of students was finite, eventually the teacher came to the student, who alreaget_ady had a hole in his badge.</p><p>After that, the teacher put a second hole in the student's badge and decided that he is done with this process, and went to the sauna.</p><p>You don't know the first student who was caught by the teacher. However, you know all the numbers $$$p_i$$$. Your task is to find out for every student $$$a$$$, who would be the student with two holes in the badge if the first caught student was $$$a$$$.</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line of the input contains the only integer $$$n$$$ ($$$1 \\le n \\le 1000$$$)\u00a0\u2014 the number of the naughty students.</p><p>The second line contains $$$n$$$ integers $$$p_1$$$, ..., $$$p_n$$$ ($$$1 \\le p_i \\le n$$$), where $$$p_i$$$ indicates the student who was reported to the teacher by student $$$i$$$.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>For every student $$$a$$$ from $$$1$$$ to $$$n$$$ print which student would receive two holes in the badge, if $$$a$$$ was the first student caught by the teacher.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Examples</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>3<br/>2 3 2<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>2 2 3 <br/></pre></div><div class=\"input\"><div class=\"title\">Input</div><pre>3<br/>1 2 3<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>1 2 3 <br/></pre></div></div></div><div class=\"note\"><div class=\"section-title\">Note</div><p>The picture corresponds to the first example test case.</p><center> <img class=\"tex-graphics\" src=\"https://espresso.codeforces.com/2a768be595f226bb844954f3e1b020fac268bb8c.png\" style=\"max-width: 100.0%;max-height: 100.0%;\"/> </center><p>When $$$a = 1$$$, the teacher comes to students $$$1$$$, $$$2$$$, $$$3$$$, $$$2$$$, in this order, and the student $$$2$$$ is the one who receives a second hole in his badge.</p><p>When $$$a = 2$$$, the teacher comes to students $$$2$$$, $$$3$$$, $$$2$$$, and the student $$$2$$$ gets a second hole in his badge. When $$$a = 3$$$, the teacher will visit students $$$3$$$, $$$2$$$, $$$3$$$ with student $$$3$$$ getting a second hole in his badge.</p><p>For the second example test case it's clear that no matter with whom the teacher starts, that student would be the one who gets the second hole in his badge.</p></div></div>",
  "pretests": [
    {
      "input": "3\r\n2 3 2",
      "output": "2 2 3"
    },
    {
      "input": "3\r\n1 2 3",
      "output": "1 2 3"
    },
    {
      "input": "3\r\n2 3 1",
      "output": "1 2 3"
    },
    {
      "input": "1\r\n1",
      "output": "1"
    },
    {
      "input": "2\r\n2 1",
      "output": "1 2"
    },
    {
      "input": "100\r\n1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100"
    },
    {
      "input": "1000\r\n895 945 666 967 619 544 253 452 120 450 633 6 544 572 8 452 343 692 475 155 513 357 224 789 576 231 115 538 121 191 71 477 355 778 584 578 590 351 398 973 956 982 303 850 994 885 402 309 154 750 514 744 1 2 3 4 5 7 9 10 11 12 13 14 15 16 17 18 19 20 477 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 538 64 65 66 67 450 191 68 69 70 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 7...",
      "output": "895 945 666 967 619 6 253 8 120 450 633 6 544 572 8 452 343 692 475 155 513 357 224 789 576 231 115 538 121 191 71 477 355 778 584 578 590 351 398 973 956 982 303 850 994 885 402 309 154 750 514 744 895 945 666 967 619 253 120 450 633 6 544 572 8 452 343 692 475 155 71 513 357 224 789 576 231 115 538 121 191 71 477 355 778 584 578 590 351 398 973 956 982 303 850 994 885 402 309 154 750 514 744 895 945 666 967 619 253 120 450 633 6 544 115 572 8 452 343 120 121 692 475 155 513 357 224 789 576 231 115 538 12..."
    },
    {
      "input": "1000\r\n894 197 325 232 902 183 41 481 495 266 152 704 790 458 546 258 30 366 747 546 332 816 523 683 771 152 647 967 785 793 62 915 864 667 972 536 678 183 290 164 533 374 932 943 508 627 226 823 644 596 767 620 563 613 53 340 813 164 591 752 990 342 326 157 97 25 197 373 732 224 693 539 826 835 642 914 775 628 75 951 920 394 246 858 505 914 585 410 820 657 234 262 329 643 737 884 616 559 713 541 481 513 570 247 940 479 474 138 737 877 599 900 530 41 526 469 4 295 624 83 66 798 784 56 586 160 806 759 213 34...",
      "output": "479 98 70 754 906 754 536 479 759 754 754 705 98 98 98 754 775 70 754 98 754 98 479 754 754 754 754 559 775 775 98 536 906 70 479 536 98 754 70 479 536 754 754 775 70 759 536 823 70 705 536 70 536 98 536 98 754 479 479 775 448 98 775 754 754 754 98 705 775 70 754 906 479 479 775 128 775 906 775 98 560 754 448 754 98 128 70 479 754 70 775 906 98 560 536 70 754 98 536 541 479 906 103 98 754 106 70 479 536 98 479 314 70 536 479 70 754 98 536 448 754 754 98 98 479 70 70 128 754 98 314 775 98 560 479 128 98 479..."
    },
    {
      "input": "1000\r\n27 224 443 344 811 120 666 185 560 276 551 80 695 989 180 15 198 928 450 26 750 671 353 125 115 30 781 888 886 729 112 643 655 267 367 999 640 341 623 853 488 269 922 474 782 787 576 899 516 381 197 245 303 510 754 96 808 250 731 634 43 84 82 566 467 859 142 70 704 127 368 52 308 191 286 348 621 155 794 31 821 202 814 465 123 150 786 509 585 390 706 867 454 32 420 73 364 214 935 351 758 315 648 996 413 713 890 595 217 982 822 374 871 944 815 182 165 92 475 131 694 513 288 48 273 774 333 681 13 657 12...",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155..."
    },
    {
      "input": "100\r\n15 14 32 65 28 96 33 93 48 28 57 20 32 20 90 42 57 53 18 58 94 21 27 29 37 22 94 45 67 60 83 23 20 23 35 93 3 42 6 46 68 46 34 25 17 16 50 5 49 91 23 76 69 100 58 68 81 32 88 41 64 29 37 13 95 25 6 59 74 58 31 35 16 80 13 80 10 59 85 18 16 70 51 40 44 28 8 76 8 87 53 86 28 100 2 73 14 100 52 9",
      "output": "16 16 16 16 16 16 16 16 16 16 16 16 16 16 16 16 16 18 18 16 16 16 16 16 16 16 16 16 16 80 16 16 16 16 35 16 16 42 16 46 80 42 16 16 16 46 53 16 49 53 16 80 53 16 16 80 16 16 80 80 16 16 16 16 16 16 16 80 69 16 16 35 16 74 16 80 16 80 16 80 16 16 16 46 16 16 16 80 16 16 53 16 16 16 16 16 16 16 80 16"
    },
    {
      "input": "100\r\n1 1 2 1 1 3 6 5 5 4 8 4 4 3 14 10 14 8 13 12 18 8 3 7 1 12 10 9 17 26 30 21 11 29 19 20 25 17 10 9 26 6 40 42 29 2 24 14 25 6 41 47 24 21 46 28 8 30 2 19 41 54 43 23 1 65 21 19 35 58 8 71 59 12 2 13 4 16 7 22 58 26 44 1 12 14 80 19 12 43 77 21 54 41 94 37 61 28 82 30",
      "output": "1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1"
    },
    {
      "input": "100\r\n27 63 53 6 56 68 61 70 35 92 9 62 38 80 90 67 96 64 58 40 14 88 82 95 18 21 65 3 57 22 59 66 47 51 34 69 20 76 41 10 99 5 42 49 81 31 19 93 23 17 74 87 43 71 78 36 8 97 50 100 28 60 24 55 91 98 26 77 30 32 12 29 44 16 86 89 54 2 7 84 52 85 73 79 75 33 83 1 94 45 46 4 13 15 48 25 37 11 72 39",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100"
    },
    {
      "input": "100\r\n87 92 91 32 27 16 50 61 48 89 9 35 10 22 17 62 44 66 23 42 54 20 79 58 3 47 81 73 34 95 37 28 45 56 99 18 12 26 68 31 40 60 4 46 25 21 90 15 53 97 41 95 59 39 80 71 8 13 77 55 19 72 88 11 86 74 94 43 24 51 83 84 6 5 33 96 100 52 36 85 69 2 38 65 29 98 57 7 78 70 82 63 14 1 76 49 93 75 67 64",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 95 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100"
    },
    {
      "input": "100\r\n22 48 66 5 59 47 9 88 65 54 44 67 10 97 93 53 21 62 55 77 6 51 60 41 39 82 76 98 98 90 23 7 83 42 85 18 73 1 94 14 40 57 26 61 75 26 68 80 33 31 27 3 36 2 91 67 81 69 30 84 63 35 15 87 70 16 71 34 49 19 25 64 64 46 8 28 4 37 90 20 13 69 89 38 78 22 74 24 56 95 50 22 52 96 45 17 32 11 46 71",
      "output": "1 2 3 4 5 6 7 8 9 10 11 67 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 98 30 31 32 33 34 35 36 37 38 39 40 41 42 26 44 45 46 47 48 49 50 51 52 53 54 55 56 57 69 59 60 61 62 63 64 65 66 67 68 69 70 71 64 73 74 75 76 77 78 90 80 81 82 83 84 85 22 87 88 89 90 91 22 93 94 95 96 97 98 46 71"
    },
    {
      "input": "100\r\n73 81 39 85 48 49 37 20 66 41 79 32 54 71 31 50 48 29 10 85 81 20 20 20 48 54 70 40 71 31 49 77 50 33 12 87 19 12 54 39 87 10 20 39 81 18 70 53 86 7 33 37 62 9 77 54 50 30 70 81 66 12 41 12 20 23 87 73 91 75 94 49 18 71 81 32 79 85 30 94 48 10 41 62 73 90 40 70 90 91 33 100 79 99 62 71 53 66 92 70",
      "output": "73 81 39 85 48 49 7 20 9 10 79 12 54 71 31 50 48 18 19 20 81 20 23 20 48 54 70 40 29 30 31 32 33 33 12 87 37 12 39 40 41 10 20 39 81 18 70 48 49 50 33 37 53 54 77 54 50 30 70 81 66 62 41 12 20 66 87 73 91 70 71 49 73 71 75 32 77 85 79 94 81 10 41 62 85 86 87 70 90 90 91 92 79 94 62 71 53 66 99 100"
    },
    {
      "input": "100\r\n90 18 99 80 82 57 97 11 92 14 67 61 93 30 87 44 29 96 85 73 55 77 12 38 8 48 22 86 64 7 58 74 9 6 65 1 24 53 98 41 45 37 59 94 66 71 83 81 3 4 89 63 50 51 75 62 70 84 36 42 25 28 2 95 56 100 47 76 27 23 26 39 91 69 19 13 16 15 21 72 20 49 88 40 54 5 43 10 78 35 68 32 17 34 79 31 60 52 33 46",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100"
    },
    {
      "input": "100\r\n73 72 15 88 11 1 2 3 4 5 73 6 7 8 88 9 10 12 13 14 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 15 72 67 68 69 70 71 74 75 76 77 78 79 80 81 82 11 83 84 85 86 87 89 90 91 92 93 94 95",
      "output": "73 72 15 88 11 73 72 15 88 11 11 73 72 15 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 72 73 11 73 72 15 88 11 73 72 15 88 11 73 72 15 88 88 11 73 72 15 88 11 73 72 15 88 11"
    },
    {
      "input": "100\r\n17 4 2 82 75 4 82 12 13 71 41 47 22 47 63 52 25 58 91 90 30 54 28 38 64 29 87 18 59 43 45 53 68 1 17 25 64 33 50 9 78 13 24 22 53 54 63 21 61 9 30 91 1 21 43 49 24 67 20 38 26 33 52 50 68 11 79 11 41 78 56 99 23 5 2 28 18 99 10 58 67 12 79 10 71 56 45 49 61 74 87 26 29 59 20 90 74 5 23 75",
      "output": "1 2 2 4 5 4 82 12 9 10 11 12 13 47 63 52 17 18 91 20 21 22 23 24 25 26 87 28 29 30 45 53 33 1 17 25 64 38 50 9 41 13 43 22 45 54 47 21 49 50 30 52 53 54 43 56 24 58 59 38 61 33 63 64 68 11 67 68 41 78 71 99 23 74 75 28 18 78 79 58 67 82 79 10 71 56 87 49 61 90 91 26 29 59 20 90 74 5 99 75"
    },
    {
      "input": "100\r\n82 5 97 89 31 24 6 91 41 94 59 15 80 16 87 55 98 49 13 47 40 45 64 34 99 65 25 95 27 71 17 63 45 85 29 81 84 58 77 23 33 96 35 26 56 66 78 36 68 3 43 20 100 83 11 48 53 30 61 12 39 56 67 72 79 21 37 8 48 86 74 76 36 52 28 38 44 18 46 42 10 2 93 7 54 92 4 81 19 1 60 90 50 70 9 32 51 57 75 14",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 45 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 56 63 64 65 66 67 68 48 70 71 72 36 74 75 76 77 78 79 80 81 82 83 84 85 86 87 81 89 90 91 92 93 94 95 96 97 98 99 100"
    },
    {
      "input": "1000\r\n1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 1...",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155..."
    },
    {
      "input": "1000\r\n1 1 1 1 4 2 3 5 1 7 6 6 12 11 8 6 2 15 18 17 6 21 14 14 3 21 20 1 23 1 3 31 19 26 13 32 24 31 29 23 4 10 16 24 27 28 33 19 39 39 46 40 28 9 7 53 28 13 26 41 52 51 12 60 5 37 7 39 37 21 24 18 67 42 27 42 70 31 8 17 71 58 36 39 38 35 78 34 2 18 67 47 58 11 91 92 36 97 51 44 41 25 21 73 15 45 105 9 22 85 57 82 100 78 13 96 53 42 65 21 3 98 110 75 44 86 30 26 79 119 122 19 106 11 76 82 31 91 42 114 50 23 48 32 93 28 94 34 4 81 130 137 146 40 19 20 114 29 18 141 6 5 81 72 35 26 92 65 107 119 127 109 6 114...",
      "output": "1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1..."
    },
    {
      "input": "1000\r\n313 452 187 511 507 859 773 881 926 346 772 111 808 780 145 783 803 932 921 55 645 244 551 246 425 725 374 910 997 343 607 789 133 802 532 925 518 118 797 843 96 261 750 917 265 845 728 642 262 944 752 166 208 983 217 61 624 776 212 505 189 867 815 660 861 715 448 422 141 889 238 785 16 195 303 575 381 528 127 536 964 314 927 430 179 729 604 897 414 570 68 809 698 793 194 113 856 497 931 7 152 328 544 65 687 495 92 935 907 940 433 887 999 149 515 393 102 220 167 373 233 894 908 814 317 798 325 402 66...",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155..."
    },
    {
      "input": "1000\r\n46 425 85 463 119 717 911 290 872 681 253 93 870 600 855 10 672 865 816 163 658 460 782 355 621 751 994 321 890 115 387 176 491 569 604 341 229 772 265 288 648 407 401 568 200 947 255 653 371 216 733 599 625 271 894 77 254 795 739 805 857 918 629 763 707 756 71 998 962 899 179 516 221 759 781 308 160 777 336 382 893 22 352 891 410 787 353 580 660 663 970 884 551 433 735 89 992 91 347 982 138 168 823 708 686 461 742 853 369 50 636 467 377 211 378 806 977 785 620 452 204 526 2 43 812 381 313 803 80 908...",
      "output": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 686 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155..."
    },
    {
      "input": "1000\r\n700 651 361 17 162 378 711 485 89 95 292 826 718 212 286 442 726 484 778 289 257 886 123 118 338 180 546 856 444 420 357 397 893 538 501 933 233 151 376 637 359 142 955 167 16 205 691 898 685 491 450 598 846 52 661 727 594 295 211 268 424 554 315 401 561 226 461 539 414 786 480 922 230 664 997 185 422 604 884 329 112 78 631 344 610 666 384 899 895 977 84 584 699 986 416 26 392 577 291 75 463 773 878 783 332 924 596 847 799 777 761 667 810 1 284 996 244 544 447 536 427 707 68 354 902 335 208 571 946 7...",
      "output": "1 2 3 17 5 6 7 485 9 10 11 12 718 14 15 16 17 18 19 20 21 22 23 24 338 26 27 28 29 30 31 397 33 34 35 36 37 38 39 40 359 42 43 44 45 46 47 48 685 50 450 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 480 922 73 74 75 76 77 78 79 80 81 82 631 84 85 86 87 88 89 90 91 92 93 986 95 96 97 577 99 75 101 102 878 104 105 106 107 847 109 777 111 112 113 114 115 116 117 118 119 120 121 122 123 354 902 126 127 128 129 130 831 132 133 134 135 136 137 138 139 140 141 142 822 144 145 146 147 148 149 150 151 15..."
    },
    {
      "input": "1000\r\n871 232 599 901 31 409 498 758 12 472 99 224 275 792 708 812 442 802 63 726 706 756 705 566 727 180 750 153 209 197 870 936 618 955 230 720 980 176 417 709 410 2 743 545 33 752 582 408 739 869 201 285 462 782 166 522 510 678 505 656 300 751 238 873 567 105 441 462 413 480 340 727 271 831 565 709 435 600 739 811 119 908 708 618 566 487 462 485 424 96 600 844 351 780 176 363 471 441 868 92 869 582 647 756 329 290 500 32 849 111 240 811 175 873 447 751 264 445 249 137 381 502 122 822 567 72 747 31 376 2...",
      "output": "1 2 599 901 31 409 7 8 12 10 99 12 275 14 708 812 442 802 63 726 706 22 705 566 727 180 750 153 29 30 31 32 33 955 230 720 980 176 417 709 410 2 743 44 45 752 582 48 739 869 51 285 462 782 166 56 510 678 505 60 300 751 63 873 567 105 441 462 413 480 71 72 73 74 75 709 435 600 79 811 81 908 708 618 85 86 462 88 424 90 91 92 93 780 95 96 471 441 99 92 869 102 647 756 105 290 500 108 849 110 111 811 175 873 447 751 264 445 119 137 381 122 122 822 567 126 747 31 376 130 439 12 133 334 815 281 137 138 522 395 1..."
    },
    {
      "input": "1000\r\n372 797 823 457 102 423 973 438 282 945 667 631 615 983 598 465 367 164 427 511 687 825 148 571 453 520 876 664 595 198 721 510 458 834 851 662 957 882 600 412 780 981 742 59 122 299 937 942 647 720 818 124 587 94 288 298 906 779 407 767 348 269 183 861 472 900 505 839 231 482 729 134 668 191 494 548 622 717 212 609 972 328 40 157 525 969 760 471 496 474 805 544 527 259 698 372 203 349 266 232 362 973 105 110 999 46 299 629 62 46 269 754 588 584 397 512 685 665 646 766 964 937 16 288 931 465 400 850 ...",
      "output": "372 2 3 457 102 6 973 438 9 945 11 631 615 14 15 16 367 164 427 20 687 825 23 571 453 26 27 664 29 198 721 32 458 834 851 36 37 882 39 40 41 42 742 44 122 46 937 942 49 50 51 124 53 54 288 56 906 58 59 60 61 62 63 64 65 66 505 839 231 482 71 72 73 191 75 548 622 78 79 80 81 82 83 157 525 86 760 471 89 90 805 92 93 94 95 96 203 349 266 100 362 102 103 110 105 46 299 629 62 110 269 112 588 584 397 116 117 665 119 766 121 122 16 124 125 465 127 128 393 384 947 132 246 134 27 876 137 431 613 140 6 423 659 572 ..."
    },
    {
      "input": "1000\r\n659 556 881 241 39 129 537 112 533 79 371 628 122 839 802 53 605 978 823 620 470 795 596 60 323 879 758 540 464 23 951 869 611 601 86 985 250 555 885 385 760 111 715 972 652 377 734 271 168 581 676 136 567 809 18 739 929 227 560 901 993 538 346 895 924 829 6 521 405 779 172 719 906 634 13 952 528 928 80 178 76 180 683 22 874 791 613 242 210 784 16 685 135 212 282 482 768 1000 608 932 303 406 912 255 477 875 576 457 382 834 894 803 630 714 642 825 658 918 914 215 89 989 468 191 141 851 640 203 600 75 ...",
      "output": "659 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 611 601 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 538 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 630 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 220 152 153 15..."
    }
  ],
  "reference_solution": {
    "submission_id": 326470182,
    "submission_url": "https://codeforces.com/contest/1020/submission/326470182",
    "author_handle": "AgOH",
    "author_rating": null,
    "language": "C++23 (GCC 14-64, msys2)",
    "code": "#include <bits/stdc++.h>\nusing namespace std;\nconst int N = 1005;\nint p[N];\nbool vis[N];\nint main()\n{\n    cin.tie(nullptr)->sync_with_stdio(false);\n    int n;\n    cin>>n;\n    for(int i=1;i<=n;i++) cin>>p[i];\n    for(int i=1;i<=n;i++)\n    {\n        // Floyd \u627e\u73af\u7b97\u6cd5\n        // \u601d\u60f3\uff1a\u53cc\u6307\u9488\u4e4b\u5feb\u6162\u6307\u9488\n        int slow=i, fast=i;\n        do\n        {\n            slow = p[slow];\n            fast = p[p[fast]];\n        }\n        while(slow!=fast);\n        int j = i;\n        while(j!=slow)\n        {\n            j = p[j];\n            slow = p[slow];\n        }\n        cout<<j<<\" \\n\"[i==n];\n    }\n}"
  },
  "verified_pseudocode": null,
  "verified_solution_code": null
}
```

## Problem: 1003A

```json
{
  "problem_id": "1003A",
  "problem_url": "https://codeforces.com/problemset/problem/1003/A",
  "problem_metadata": {
    "name": "Polycarp's Pockets",
    "tags": [
      "implementation"
    ],
    "time_limit_ms": 1000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">A. Polycarp's Pockets</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>1 second</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\"><div class=\"property-title\">input</div>standard input</div><div class=\"output-file output-standard\"><div class=\"property-title\">output</div>standard output</div></div><div><p>Polycarp has $$$n$$$ coins, the value of the $$$i$$$-th coin is $$$a_i$$$. Polycarp wants to distribute all the coins between his pockets, but he cannot put two coins with the same value into the same pocket.</p><p>For example, if Polycarp has got six coins represented as an array $$$a = [1, 2, 4, 3, 3, 2]$$$, he can distribute the coins into two pockets as follows: $$$[1, 2, 3], [2, 3, 4]$$$.</p><p>Polycarp wants to distribute all the coins with the minimum number of used pockets. Help him to do that.</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line of the input contains one integer $$$n$$$ ($$$1 \\le n \\le 100$$$) \u2014 the number of coins.</p><p>The second line of the input contains $$$n$$$ integers $$$a_1, a_2, \\dots, a_n$$$ ($$$1 \\le a_i \\le 100$$$) \u2014 values of coins.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>Print only one integer \u2014 the minimum number of pockets Polycarp needs to distribute all the coins so no two coins with the same value are put into the same pocket.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Examples</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>6<br/>1 2 4 3 3 2<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>2<br/></pre></div><div class=\"input\"><div class=\"title\">Input</div><pre>1<br/>100<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>1<br/></pre></div></div></div></div>",
  "pretests": [
    {
      "input": "6\r\n1 2 4 3 3 2",
      "output": "2"
    },
    {
      "input": "1\r\n100",
      "output": "1"
    },
    {
      "input": "100\r\n100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100",
      "output": "100"
    },
    {
      "input": "100\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "100"
    },
    {
      "input": "100\r\n59 47 39 47 47 71 47 28 58 47 35 79 58 47 38 47 47 47 47 27 47 43 29 95 47 49 46 71 47 74 79 47 47 32 45 67 47 47 30 37 47 47 16 67 22 76 47 86 84 10 5 47 47 47 47 47 1 51 47 54 47 8 47 47 9 47 47 47 47 28 47 47 26 47 47 47 47 47 47 92 47 47 77 47 47 24 45 47 10 47 47 89 47 27 47 89 47 67 24 71",
      "output": "51"
    },
    {
      "input": "100\r\n45 99 10 27 16 85 39 38 17 32 15 23 67 48 50 97 42 70 62 30 44 81 64 73 34 22 46 5 83 52 58 60 33 74 47 88 18 61 78 53 25 95 94 31 3 75 1 57 20 54 59 9 68 7 77 43 21 87 86 24 4 80 11 49 2 72 36 84 71 8 65 55 79 100 41 14 35 89 66 69 93 37 56 82 90 91 51 19 26 92 6 96 13 98 12 28 76 40 63 29",
      "output": "1"
    },
    {
      "input": "100\r\n45 29 5 2 6 50 22 36 14 15 9 48 46 20 8 37 7 47 12 50 21 38 18 27 33 19 40 10 5 49 38 42 34 37 27 30 35 24 10 3 40 49 41 3 4 44 13 25 28 31 46 36 23 1 1 23 7 22 35 26 21 16 48 42 32 8 11 16 34 11 39 32 47 28 43 41 39 4 14 19 26 45 13 18 15 25 2 44 17 29 17 33 43 6 12 30 9 20 31 24",
      "output": "2"
    },
    {
      "input": "50\r\n7 7 3 3 7 4 5 6 4 3 7 5 6 4 5 4 4 5 6 7 7 7 4 5 5 5 3 7 6 3 4 6 3 6 4 4 5 4 6 6 3 5 6 3 5 3 3 7 7 6",
      "output": "10"
    },
    {
      "input": "100\r\n100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 99 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100",
      "output": "99"
    },
    {
      "input": "7\r\n1 2 3 3 3 1 2",
      "output": "3"
    },
    {
      "input": "5\r\n1 2 3 4 5",
      "output": "1"
    },
    {
      "input": "7\r\n1 2 3 4 5 6 7",
      "output": "1"
    },
    {
      "input": "8\r\n1 2 3 4 5 6 7 8",
      "output": "1"
    },
    {
      "input": "9\r\n1 2 3 4 5 6 7 8 9",
      "output": "1"
    },
    {
      "input": "10\r\n1 2 3 4 5 6 7 8 9 10",
      "output": "1"
    },
    {
      "input": "3\r\n2 1 1",
      "output": "2"
    },
    {
      "input": "11\r\n1 2 3 4 5 6 7 8 9 1 1",
      "output": "3"
    },
    {
      "input": "12\r\n1 2 1 1 1 1 1 1 1 1 1 1",
      "output": "11"
    },
    {
      "input": "13\r\n1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "13"
    },
    {
      "input": "14\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "14"
    },
    {
      "input": "15\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "15"
    },
    {
      "input": "16\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "16"
    },
    {
      "input": "3\r\n1 1 1",
      "output": "3"
    },
    {
      "input": "3\r\n1 2 3",
      "output": "1"
    },
    {
      "input": "10\r\n1 1 1 1 2 2 1 1 9 10",
      "output": "6"
    },
    {
      "input": "2\r\n1 1",
      "output": "2"
    },
    {
      "input": "56\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "56"
    },
    {
      "input": "99\r\n35 96 73 72 70 83 22 93 98 75 45 32 81 82 45 54 25 7 53 72 29 2 94 19 21 98 34 28 39 99 55 85 44 23 6 47 98 2 33 34 19 57 49 35 67 4 60 4 4 23 55 6 57 66 16 68 34 45 84 79 48 63 4 9 46 88 98 13 19 27 83 12 4 63 57 22 44 77 44 62 28 52 44 64 9 24 55 22 48 4 2 9 80 76 45 1 56 22 92",
      "output": "6"
    },
    {
      "input": "10\r\n1 2 2 3 3 3 4 4 4 4",
      "output": "4"
    },
    {
      "input": "99\r\n97 44 33 56 42 10 61 85 64 26 40 39 82 34 75 9 51 51 39 73 58 38 74 31 13 99 58 1 28 89 76 19 52 7 40 56 12 27 72 72 67 75 62 46 22 55 35 16 18 39 60 63 92 42 85 69 34 61 73 50 57 95 30 4 45 63 76 58 32 35 48 81 10 78 95 79 55 97 21 21 22 94 30 17 78 57 89 93 100 44 16 89 68 55 19 46 42 73 21",
      "output": "3"
    },
    {
      "input": "5\r\n5 5 5 5 1",
      "output": "4"
    },
    {
      "input": "6\r\n2 3 2 5 2 6",
      "output": "3"
    },
    {
      "input": "3\r\n58 59 58",
      "output": "2"
    },
    {
      "input": "9\r\n1 2 3 4 5 6 7 8 8",
      "output": "2"
    },
    {
      "input": "97\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1",
      "output": "97"
    },
    {
      "input": "3\r\n95 95 4",
      "output": "2"
    },
    {
      "input": "3\r\n2 2 5",
      "output": "2"
    }
  ],
  "reference_solution": {
    "submission_id": 330106904,
    "submission_url": "https://codeforces.com/contest/1003/submission/330106904",
    "author_handle": "lehaleha_2010",
    "author_rating": null,
    "language": "C++17 (GCC 7-32)",
    "code": "#include <bits/stdc++.h>\nusing namespace std;\n int main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n     int  n; cin >> n;\n    unordered_map<int, int> done;\n   int max_ = 0, curr;\n   while (n--){\n      cin >> curr;\n      done[curr]++;\n      max_ = max(done[curr], max_);\n           }\n     cout << max_;\n}"
  },
  "verified_pseudocode": "// Time Complexity: O(N) where N is the number of coins.\n// Space Complexity: O(M) where M is the range of possible coin values (100 in this problem), or O(D) where D is the number of distinct coin values, whichever is smaller. Effectively O(1) because M is a small constant.\n\nFUNCTION solve():\n  READ N\n  DECLARE coin_counts_map AS MAP<INTEGER, INTEGER> // Stores the frequency of each distinct coin value\n  DECLARE max_frequency = 0\n\n  FOR i FROM 1 TO N:\n    READ current_coin_value\n    // Increment the count for the current coin value\n    IF current_coin_value IS IN coin_counts_map THEN\n      coin_counts_map[current_coin_value] = coin_counts_map[current_coin_value] + 1\n    ELSE\n      coin_counts_map[current_coin_value] = 1\n    END IF\n    \n    // Update the maximum frequency found so far\n    max_frequency = MAX(max_frequency, coin_counts_map[current_coin_value])\n\n  PRINT max_frequency\n\n// Main program execution\nCALL solve()\n",
  "verified_solution_code": "#include <bits/stdc++.h>\nusing namespace std;\n\nvoid solve() {\n  int N;\n  cin >> N;\n  map<int, int> coin_counts_map;\n  int max_frequency = 0;\n\n  for (int i = 1; i <= N; i++) {\n    int current_coin_value;\n    cin >> current_coin_value;\n\n    if (coin_counts_map.find(current_coin_value) != coin_counts_map.end()) {\n      coin_counts_map[current_coin_value]++;\n    } else {\n      coin_counts_map[current_coin_value] = 1;\n    }\n\n    max_frequency = max(max_frequency, coin_counts_map[current_coin_value]);\n  }\n\n  cout << max_frequency << endl;\n}\n\nint main() {\n  ios_base::sync_with_stdio(false);\n  cin.tie(NULL);\n  int t = 1;\n  while (t--) {\n    solve();\n  }\n  return 0;\n}",
  "code_quality_analysis": {
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {
      "oracle_0": {
        "rating": "Excellent",
        "justification": "The oracle correctly identifies that the minimum number of pockets required is equal to the maximum frequency of any coin value. It uses an `unordered_map` to efficiently count frequencies of each coin value in a single pass (O(N) on average) and tracks the maximum frequency seen. This approach is optimal in time complexity and efficient in space complexity given the constraints (coin values up to 100, so map size is at most 100). It handles all specified edge cases (e.g., N=1, all distinct coins, all same coins) correctly."
      }
    }
  }
}
```

## Problem: 1003C

```json
{
  "problem_id": "1003C",
  "problem_url": "https://codeforces.com/problemset/problem/1003/C",
  "problem_metadata": {
    "name": "Intense Heat",
    "tags": [
      "brute force",
      "implementation",
      "math"
    ],
    "time_limit_ms": 4000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">C. Intense Heat</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>4 seconds</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\"><div class=\"property-title\">input</div>standard input</div><div class=\"output-file output-standard\"><div class=\"property-title\">output</div>standard output</div></div><div><p>The heat during the last few days has been really intense. Scientists from all over the Berland study how the temperatures and weather change, and they claim that this summer is abnormally hot. But any scientific claim sounds a lot more reasonable if there are some numbers involved, so they have decided to actually calculate some value which would represent how high the temperatures are.</p><p>Mathematicians of Berland State University came up with a special <span class=\"tex-font-style-it\">heat intensity value</span>. This value is calculated as follows:</p><p>Suppose we want to analyze the segment of $$$n$$$ consecutive days. We have measured the temperatures during these $$$n$$$ days; the temperature during $$$i$$$-th day equals $$$a_i$$$.</p><p>We denote the <span class=\"tex-font-style-it\">average temperature</span> of a segment of some consecutive days as the arithmetic mean of the temperature measures during this segment of days. So, if we want to analyze the <span class=\"tex-font-style-it\">average temperature</span> from day $$$x$$$ to day $$$y$$$, we calculate it as $$$\\frac{\\sum \\limits_{i = x}^{y} a_i}{y - x + 1}$$$ (note that division is performed without any rounding). The <span class=\"tex-font-style-it\">heat intensity value</span> is the maximum of <span class=\"tex-font-style-it\">average temperatures</span> over all segments of not less than $$$k$$$ consecutive days. For example, if analyzing the measures $$$[3, 4, 1, 2]$$$ and $$$k = 3$$$, we are interested in segments $$$[3, 4, 1]$$$, $$$[4, 1, 2]$$$ and $$$[3, 4, 1, 2]$$$ (we want to find the maximum value of <span class=\"tex-font-style-it\">average temperature</span> over these segments).</p><p>You have been hired by Berland State University to write a program that would compute the <span class=\"tex-font-style-it\">heat intensity value</span> of a given period of days. Are you up to this task?</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line contains two integers $$$n$$$ and $$$k$$$ ($$$1 \\le k \\le n \\le 5000$$$) \u2014 the number of days in the given period, and the minimum number of days in a segment we consider when calculating <span class=\"tex-font-style-it\">heat intensity value</span>, respectively.</p><p>The second line contains $$$n$$$ integers $$$a_1$$$, $$$a_2$$$, ..., $$$a_n$$$ ($$$1 \\le a_i \\le 5000$$$) \u2014 the temperature measures during given $$$n$$$ days.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>Print one real number \u2014 the <span class=\"tex-font-style-it\">heat intensity value</span>, i. e., the maximum of <span class=\"tex-font-style-it\">average temperatures</span> over all segments of not less than $$$k$$$ consecutive days.</p><p>Your answer will be considered correct if the following condition holds: $$$|res - res_0| &lt; 10^{-6}$$$, where $$$res$$$ is your answer, and $$$res_0$$$ is the answer given by the jury's solution.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Example</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>4 3<br/>3 4 1 2<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>2.666666666666667<br/></pre></div></div></div></div>",
  "pretests": [
    {
      "input": "4 3\r\n3 4 1 2",
      "output": "2.666666666666667"
    },
    {
      "input": "5 1\r\n3 10 9 10 6",
      "output": "10.000000000000000"
    },
    {
      "input": "5 2\r\n7 3 3 1 8",
      "output": "5.000000000000000"
    },
    {
      "input": "5 3\r\n1 7 6 9 1",
      "output": "7.333333333333333"
    },
    {
      "input": "5 4\r\n5 1 10 6 1",
      "output": "5.500000000000000"
    },
    {
      "input": "5 5\r\n4 6 6 6 2",
      "output": "4.800000000000000"
    },
    {
      "input": "500 1\r\n334 311 831 968 475 813 312 415 832 58 615 943 266 93 929 68 94 922 623 506 529 922 14 229 538 329 168 930 706 583 370 532 179 488 780 480 558 364 4 425 963 503 571 532 389 378 694 365 795 696 862 985 833 426 144 890 333 932 630 254 794 638 437 432 232 51 981 726 946 365 620 729 510 303 835 808 913 402 215 685 305 369 985 502 345 556 903 629 616 585 593 417 858 6 756 747 437 137 267 698 878 304 281 407 506 689 8 626 949 531 949 355 990 91 649 273 665 89 450 783 780 864 576 458 346 817 696 924 139 55...",
      "output": "1000.000000000000000"
    },
    {
      "input": "500 250\r\n209 335 490 169 379 666 155 431 84 566 237 86 59 79 56 372 647 264 887 465 7 766 265 672 818 86 986 586 519 627 511 522 751 153 358 25 198 284 908 700 741 426 156 705 827 445 255 758 479 202 495 842 536 4 154 738 189 545 573 133 421 620 159 145 529 354 601 708 533 541 381 803 691 252 812 398 471 193 374 2 148 953 422 198 469 360 668 422 101 874 409 163 600 3 470 569 447 1000 405 312 936 164 598 916 724 796 484 405 288 267 758 64 124 375 390 348 423 194 509 997 177 306 333 604 983 249 589 413 418 9...",
      "output": "520.498480243161112"
    },
    {
      "input": "500 500\r\n64 67 936 512 641 357 801 500 528 638 133 856 655 726 495 580 61 585 120 157 570 973 243 996 230 221 690 655 282 873 583 407 925 20 796 57 952 133 804 973 123 206 559 202 518 512 698 496 376 565 533 604 68 53 571 312 727 906 125 464 884 19 823 846 640 669 98 478 677 661 1000 451 499 447 804 472 459 442 887 144 986 842 540 967 196 501 773 687 63 862 427 932 699 398 450 56 985 701 898 792 169 501 743 516 378 488 674 163 798 485 183 733 891 927 933 775 795 454 81 123 717 700 291 365 466 600 790 671 1...",
      "output": "508.911999999999978"
    },
    {
      "input": "1000 1\r\n782 794 893 528 928 143 687 731 655 271 265 335 892 645 757 418 892 646 769 785 943 907 72 146 306 475 17 211 934 694 486 448 199 75 167 817 981 563 989 897 206 867 335 856 234 526 144 914 782 89 590 134 66 966 773 169 707 9 394 432 17 94 697 233 162 377 848 139 982 732 473 937 520 221 396 754 51 789 930 276 979 250 195 989 672 590 729 857 959 933 899 479 128 11 451 940 169 740 888 966 577 802 717 145 158 99 144 662 480 257 172 935 571 744 55 509 825 570 605 442 662 934 491 431 266 941 477 375 219 ...",
      "output": "1000.000000000000000"
    },
    {
      "input": "1000 500\r\n139 25 688 669 971 732 117 619 742 96 229 75 504 554 141 481 80 539 399 379 659 326 160 765 159 662 970 883 689 286 307 427 216 111 133 992 151 821 276 216 783 970 371 559 474 962 543 994 577 998 386 325 312 681 442 982 805 374 303 687 340 87 920 776 965 431 807 218 44 218 912 869 417 416 558 803 38 646 479 715 972 756 27 703 830 623 1000 838 115 169 681 499 112 900 130 787 884 27 166 83 371 234 482 873 492 625 415 398 523 708 467 314 543 629 168 640 573 609 932 301 491 615 968 285 102 869 241 94...",
      "output": "492.899159663865532"
    },
    {
      "input": "1000 1000\r\n253 881 689 754 524 908 193 966 715 982 590 948 394 157 82 755 72 426 523 687 276 573 998 49 965 519 386 629 36 527 929 906 445 614 58 566 18 530 994 424 159 879 382 92 359 489 122 387 510 883 709 656 364 579 595 268 544 915 10 786 867 66 413 420 865 241 916 484 588 927 18 492 960 526 886 735 560 995 154 333 728 881 359 235 296 287 215 888 312 645 930 386 934 771 906 743 65 315 246 140 90 290 515 146 286 707 382 83 221 731 195 977 134 894 521 728 65 889 652 895 723 790 586 220 110 283 63 301 686...",
      "output": "506.016999999999996"
    },
    {
      "input": "5000 1\r\n650 957 951 381 998 488 827 76 763 788 968 174 797 124 953 273 674 999 120 200 549 226 866 399 508 373 583 289 354 169 67 251 821 504 456 374 137 637 458 576 171 648 761 44 262 67 435 381 770 79 431 15 160 200 250 255 831 37 582 573 818 169 935 145 744 341 708 764 187 475 892 458 417 116 30 727 926 852 807 87 800 745 624 779 314 127 830 27 434 262 841 191 970 506 749 189 978 875 747 319 476 659 977 585 199 810 598 831 814 381 895 541 646 859 221 909 83 847 389 533 795 113 182 334 617 85 502 814 20 ...",
      "output": "1000.000000000000000"
    },
    {
      "input": "5000 500\r\n302 84 246 739 612 360 166 431 258 799 68 684 494 751 997 264 138 890 814 177 874 825 414 263 465 932 537 111 676 571 598 562 237 400 986 147 929 291 660 669 779 693 366 587 311 253 714 470 463 30 755 635 354 159 40 810 832 857 636 488 607 621 240 550 417 588 432 423 892 340 626 166 16 346 826 486 101 331 97 536 762 185 817 537 767 428 171 505 148 598 201 44 200 198 892 597 19 374 519 879 523 685 114 618 691 374 584 732 160 727 73 389 851 899 569 897 553 393 23 842 670 114 63 636 733 702 576 743 ...",
      "output": "547.081510934393691"
    },
    {
      "input": "5000 1000\r\n82 25 526 483 986 987 770 803 391 842 568 77 874 848 972 378 917 447 655 544 649 697 864 530 62 513 950 766 71 839 848 694 203 264 37 128 358 948 556 654 405 447 254 343 326 592 175 284 390 524 856 844 168 12 624 416 589 731 734 927 903 857 1 660 460 491 489 427 689 352 251 39 469 469 888 47 281 186 502 213 807 763 958 22 536 537 244 140 460 118 171 383 790 444 198 31 774 575 216 308 365 742 197 735 612 870 358 414 629 487 81 996 96 525 231 870 760 816 357 383 364 340 267 901 798 2 984 265 175 5...",
      "output": "527.642220019821593"
    },
    {
      "input": "5000 1\r\n2952 4571 3774 1681 2019 3440 4153 4805 3522 3867 2841 115 282 1496 3635 298 3155 1987 2011 2119 2098 4543 702 1744 1881 1904 744 3066 4747 2867 1336 3684 4856 2817 975 3970 1791 4480 1245 1434 3807 2873 2324 1082 2316 1931 2011 4928 3521 183 2084 1104 4040 4650 1398 443 1443 4470 1715 722 1671 496 1763 3799 4076 836 1488 3196 590 4725 464 401 3815 349 3751 4274 4435 2283 1514 103 4010 744 868 2147 1289 4009 1236 3814 4673 1728 4574 1443 3415 4979 3798 3186 834 1251 4040 1903 377 4215 2947 1241 474...",
      "output": "5000.000000000000000"
    },
    {
      "input": "5000 500\r\n620 3010 2841 3760 4268 3494 1895 998 3337 864 1009 1656 2059 3536 4022 1448 421 780 437 3022 1191 4660 4759 4443 1293 285 2314 1400 4374 135 2736 893 2254 1023 2286 3098 1068 2078 325 4305 493 767 597 129 1879 125 2157 925 3863 1083 2356 2811 4995 306 2419 3910 265 4991 3593 4533 4934 642 678 3585 4720 4367 3864 19 3037 4209 2569 2971 737 770 3270 2994 2236 333 3114 1257 1658 2237 4889 4912 3249 4131 3253 4848 3398 3035 1749 4489 3480 3439 1889 1453 1396 2475 2103 4587 2079 4167 4281 1485 4551 2...",
      "output": "2719.360000000000127"
    },
    {
      "input": "3 2\r\n2 1 2",
      "output": "1.666666666666667"
    },
    {
      "input": "5000 1000\r\n4732 3188 2689 2542 352 4248 1412 1536 3440 4654 1788 2779 713 2753 258 1574 1773 2526 521 896 1768 3303 79 428 2020 2715 2744 332 3150 2260 2027 275 4710 887 4571 122 3915 4103 1335 124 4493 4603 738 1065 4513 3620 2419 4575 1153 2000 4254 1172 1049 2914 3962 4701 187 2559 2466 411 4044 362 2972 2897 2781 1073 4452 583 2314 2557 2290 4354 2886 3366 592 4681 2550 1573 2757 90 4617 2585 4748 3451 4327 4179 4078 945 631 1593 500 1324 3206 694 1501 3625 4431 4680 4350 2463 4014 1537 4645 890 244 36...",
      "output": "2568.922233300099833"
    },
    {
      "input": "5000 250\r\n4661 2278 2395 4417 4494 2507 4057 1120 4597 2304 3409 2294 2462 1593 775 4729 1711 1948 1204 4330 628 750 2485 2311 985 151 3314 2330 3803 1889 2368 2199 80 4645 1144 3258 1313 3230 3133 4735 1111 3283 1194 4928 3380 4249 1714 187 1670 4616 2318 2049 4167 257 2003 3145 1023 822 337 1202 3472 138 4821 2396 3313 2861 4367 2056 1085 385 2053 619 4337 2872 1575 728 353 83 2601 4515 1819 2540 3772 1142 3818 2885 852 287 4436 2855 1539 4424 3381 1045 4909 966 562 4774 18 1915 551 3830 2432 2589 898 10...",
      "output": "2748.933070866141861"
    },
    {
      "input": "5000 750\r\n1987 3838 4383 3789 4866 3512 3189 3114 2804 2206 231 3554 3132 3888 2256 2133 591 151 4432 4161 1132 4105 889 2004 947 3553 4515 2803 851 1404 3440 4863 753 4789 1568 4611 3176 4417 3679 3623 2892 1108 3066 2896 694 1411 2118 4485 3875 992 1769 2796 693 2034 4391 4883 1024 1185 574 4847 4534 2222 2426 4448 3116 2873 4986 731 4459 3529 1793 3399 3791 4552 4134 2608 4891 4436 3244 264 996 4592 2891 25 961 1128 4085 932 4338 1329 906 4765 3694 3694 1580 3124 4003 2468 116 2181 1113 3231 2179 185 19...",
      "output": "2638.526881720430083"
    },
    {
      "input": "5000 5000\r\n5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 500...",
      "output": "2500.500000000000000"
    },
    {
      "input": "5000 2500\r\n5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 5000 1 500...",
      "output": "2501.499400239903935"
    },
    {
      "input": "1 1\r\n5000",
      "output": "5000.000000000000000"
    },
    {
      "input": "3002 3\r\n1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1...",
      "output": "3333.666666666666515"
    }
  ],
  "reference_solution": {
    "submission_id": 329997228,
    "submission_url": "https://codeforces.com/contest/1003/submission/329997228",
    "author_handle": "Stay_Hard",
    "author_rating": null,
    "language": "C++23 (GCC 14-64, msys2)",
    "code": "#include<bits/stdc++.h>\nusing namespace std;\n#define int long long int\n signed main() {  \n    ios::sync_with_stdio(false);\n    cin.tie(NULL);\n    int n,k;\n    cin >> n >> k;\n    vector<int> v(n);\n    for(int& i : v) cin >> i;\n    vector<int> p(n);\n    p[0] = v[0];\n    for(int i=1;i<n;i++){\n        p[i] = p[i-1] + v[i];\n    }\n    long double ans = 0;\n    for(int i=0;i<n-k+1;i++){\n        for(int j=i+k-1;j<n;j++){\n            long double temp = p[j];\n            if(i != 0) temp -= p[i-1];\n            temp /= j-i+1;\n            ans = max(ans,temp);\n        }\n    }\n    cout << fixed << setprecision(7) << ans << '\\n';\n}"
  },
  "verified_pseudocode": "Function solve():\n  Read integer n (number of days) and integer k (minimum segment length).\n  Read an array `temperatures` of size n.\n\n  // Step 1: Pre-calculate prefix sums for efficient O(1) segment sum queries.\n  Create an array `prefix_sums` of size n.\n  `prefix_sums[0] = temperatures[0]`\n  For i from 1 to n-1:\n    `prefix_sums[i] = prefix_sums[i-1] + temperatures[i]`\n\n  // Step 2: Iterate through all valid segments and find the maximum average.\n  Initialize a real number `max_average` to 0.0.\n\n  // Iterate through all possible contiguous segments of length at least k.\n  // `i` is the starting index of a segment.\n  For i from 0 to n-k:\n    // `j` is the ending index of a segment.\n    For j from i+k-1 to n-1:\n      // Calculate the sum of the segment from index i to j using prefix sums.\n      If i is 0:\n        `current_sum = prefix_sums[j]`\n      Else:\n        `current_sum = prefix_sums[j] - prefix_sums[i-1]`\n      \n      `length = j - i + 1`\n      `current_average = current_sum / length`\n      \n      // Update the overall maximum average.\n      `max_average = maximum(max_average, current_average)`\n\n  // Step 3: Print the result.\n  Print `max_average` with high precision.",
  "verified_solution_code": "#include <iostream>\n#include <iomanip>\n#include <algorithm>\n#include <vector>\n\nvoid solve() {\n  int n, k;\n  std::cin >> n >> k;\n\n  std::vector<double> temperatures(n);\n  for (int i = 0; i < n; i++) {\n    std::cin >> temperatures[i];\n  }\n\n  std::vector<double> prefix_sums(n);\n  prefix_sums[0] = temperatures[0];\n  for (int i = 1; i < n; i++) {\n    prefix_sums[i] = prefix_sums[i-1] + temperatures[i];\n  }\n\n  double max_average = 0.0;\n\n  for (int i = 0; i <= n - k; i++) {\n    for (int j = i + k - 1; j < n; j++) {\n      double current_sum;\n      if (i == 0) {\n        current_sum = prefix_sums[j];\n      } else {\n        current_sum = prefix_sums[j] - prefix_sums[i-1];\n      }\n      \n      double length = j - i + 1;\n      double current_average = current_sum / length;\n      \n      max_average = std::max(max_average, current_average);\n    }\n  }\n\n  std::cout << std::fixed << std::setprecision(10) << max_average << std::endl;\n}\n\nint main() {\n  solve();\n  return 0;\n}",
  "code_quality_analysis": {
    "reference_analysis": {
      "cppcheck": {
        "errors": [
          {
            "id": "missingIncludeSystem",
            "severity": "information",
            "msg": "Include file: <bits/stdc++.h> not found. Please note: Cppcheck does not need standard library headers to get proper results."
          },
          {
            "id": "checkersReport",
            "severity": "information",
            "msg": "Active checkers: 169/966 (use --checkers-report=<filename> to see details)"
          }
        ],
        "error_counts": {
          "information": 2
        }
      },
      "semantic": {
        "error": "module 'lizard' has no attribute 'analyze_source_code'"
      }
    },
    "reconstructed_analysis": {
      "cppcheck": {
        "errors": [
          {
            "id": "missingIncludeSystem",
            "severity": "information",
            "msg": "Include file: <iostream> not found. Please note: Cppcheck does not need standard library headers to get proper results."
          },
          {
            "id": "missingIncludeSystem",
            "severity": "information",
            "msg": "Include file: <iomanip> not found. Please note: Cppcheck does not need standard library headers to get proper results."
          },
          {
            "id": "missingIncludeSystem",
            "severity": "information",
            "msg": "Include file: <algorithm> not found. Please note: Cppcheck does not need standard library headers to get proper results."
          },
          {
            "id": "missingIncludeSystem",
            "severity": "information",
            "msg": "Include file: <vector> not found. Please note: Cppcheck does not need standard library headers to get proper results."
          },
          {
            "id": "checkersReport",
            "severity": "information",
            "msg": "Active checkers: 169/966 (use --checkers-report=<filename> to see details)"
          }
        ],
        "error_counts": {
          "information": 5
        }
      },
      "semantic": {
        "error": "module 'lizard' has no attribute 'analyze_source_code'"
      }
    }
  }
}
```

## Problem: 1A

```json
{
  "problem_id": "1A",
  "problem_url": "https://codeforces.com/problemset/problem/1/A",
  "problem_metadata": {
    "name": "Theatre Square",
    "tags": [
      "math"
    ],
    "time_limit_ms": 1000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">A. Theatre Square</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>1 second</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\"><div class=\"property-title\">input</div>stdin</div><div class=\"output-file output-standard\"><div class=\"property-title\">output</div>stdout</div></div><div><p>Theatre Square in the capital city of Berland has a rectangular shape with the size <span class=\"tex-span\"><i>n</i>\u2009\u00d7\u2009<i>m</i></span> meters. On the occasion of the city's anniversary, a decision was taken to pave the Square with square granite flagstones. Each flagstone is of the size <span class=\"tex-span\"><i>a</i>\u2009\u00d7\u2009<i>a</i></span>.</p><p>What is the least number of flagstones needed to pave the Square? It's allowed to cover the surface larger than the Theatre Square, but the Square has to be covered. It's not allowed to break the flagstones. The sides of flagstones should be parallel to the sides of the Square.</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The input contains three positive integer numbers in the first line: <span class=\"tex-span\"><i>n</i>,\u2009\u2009<i>m</i></span> and <span class=\"tex-span\"><i>a</i></span> (<span class=\"tex-span\">1\u2009\u2264\u2009\u2009<i>n</i>,\u2009<i>m</i>,\u2009<i>a</i>\u2009\u2264\u200910<sup class=\"upper-index\">9</sup></span>).</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>Write the needed number of flagstones.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Examples</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input</div><pre>6 6 4<br/></pre></div><div class=\"output\"><div class=\"title\">Output</div><pre>4<br/></pre></div></div></div></div>",
  "pretests": [
    {
      "input": "6 6 4",
      "output": "4"
    },
    {
      "input": "1 1 1",
      "output": "1"
    },
    {
      "input": "2 1 1",
      "output": "2"
    },
    {
      "input": "1 2 1",
      "output": "2"
    },
    {
      "input": "2 2 1",
      "output": "4"
    },
    {
      "input": "2 1 2",
      "output": "1"
    },
    {
      "input": "1 1 3",
      "output": "1"
    },
    {
      "input": "2 3 4",
      "output": "1"
    },
    {
      "input": "1000000000 1000000000 1",
      "output": "1000000000000000000"
    },
    {
      "input": "12 13 4",
      "output": "12"
    },
    {
      "input": "222 332 5",
      "output": "3015"
    },
    {
      "input": "1000 1000 10",
      "output": "10000"
    },
    {
      "input": "1001 1000 10",
      "output": "10100"
    },
    {
      "input": "100 10001 1000000000",
      "output": "1"
    },
    {
      "input": "1000000000 1000000000 1000000000",
      "output": "1"
    },
    {
      "input": "1000000000 1000000000 999999999",
      "output": "4"
    },
    {
      "input": "1000000000 1000000000 192",
      "output": "27126743055556"
    },
    {
      "input": "1000000000 987654321 1",
      "output": "987654321000000000"
    },
    {
      "input": "456784567 1000000000 51",
      "output": "175618850864484"
    },
    {
      "input": "39916800 134217728 40320",
      "output": "3295710"
    }
  ],
  "reference_solution": {
    "submission_id": 334212759,
    "submission_url": "https://codeforces.com/contest/1/submission/334212759",
    "author_handle": "Jenin_Patel",
    "author_rating": null,
    "language": "C++17 (GCC 7-32)",
    "code": "#include<bits/stdc++.h>\n using namespace std;\n #define int long long\n#define ll long long\n#define endl \"\\n\"\n#define cy cout << \"YES\" << endl\n#define cn cout << \"NO\" << endl\n#define c1 cout<< -1 <<endl\n#define PI 3.141592653589793238462643383279\n#define all(v) (v).begin(),(v).end()\n#define rall(v) (v).rbegin(),(v).rend()\n#define pb push_back\n#define ff first\n#define ss second\nconst ll mod= 1e9 + 7;\n ll BinExp(ll a,ll b,ll m){ll ans=1;while(b>0){if(b&1){ans=(ans*1LL*a)%m;}a=(a*1LL*a)%m;b>>=1;}return ans;}\nll m_mod(ll x, ll y) { return ((x % mod) * (y % mod)) % mod;}\nll m_divmod(ll x,ll y,ll m){return (x%mod*BinExp(y,m-2,m))%m;}\nll gcd(ll a, ll b) { if (a > b)swap(a, b);  if (a == 0)  return b; return gcd(b % a, a); }\n int solve()\n{\n    int n,m,a;\n    cin>>n>>m>>a;\n    cout<<((n+a-1)/a)*((m+a-1)/a)<<endl;\n    return 0;\n}\n int32_t main(){\n    ios_base::sync_with_stdio(false);\n    cin.tie(0);\n    cout.tie(0);\n            solve();\n    }"
  },
  "verified_pseudocode": "// Time Complexity: O(1)\n// Space Complexity: O(1)\n\n// Input: Three positive integers n, m, a (1 <= n, m, a <= 10^9)\n// Output: The minimum number of a*a flagstones needed to cover an n*m rectangle.\n\nFUNCTION solve():\n  // Read n, m, a as 64-bit integers to prevent overflow, as n, m can be up to 10^9 and their product can be up to 10^18.\n  READ n, m, a\n\n  // Calculate the number of flagstones needed along the 'n' dimension.\n  // Using (n + a - 1) / a for integer division is equivalent to ceil(n / a).\n  num_tiles_n = (n + a - 1) / a\n\n  // Calculate the number of flagstones needed along the 'm' dimension.\n  num_tiles_m = (m + a - 1) / a\n\n  // The total number of flagstones is the product of tiles needed in each dimension.\n  total_flagstones = num_tiles_n * num_tiles_m\n\n  PRINT total_flagstones\n",
  "verified_solution_code": "#include <bits/stdc++.h>\nusing namespace std;\n\nlong long calculateFlagstones(long long n, long long m, long long a) {\n  long long num_tiles_n = (n + a - 1) / a;\n  long long num_tiles_m = (m + a - 1) / a;\n  return num_tiles_n * num_tiles_m;\n}\n\nint main() {\n  ios_base::sync_with_stdio(false);\n  cin.tie(NULL);\n  long long n, m, a;\n  cin >> n >> m >> a;\n  cout << calculateFlagstones(n, m, a) << endl;\n  return 0;\n}",
  "code_quality_analysis": {
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {
      "oracle_0": {
        "rating": "Excellent",
        "justification": "The solution correctly identifies the need for 64-bit integers by using `#define int long long`. It implements the optimal O(1) approach for calculating `ceil(L/a)` using integer division `(L + a - 1) / a` for both dimensions and then multiplying the results. This handles all constraints and edge cases efficiently and precisely."
      }
    }
  }
}
```

## Problem: 71A

```json
{
  "problem_id": "71A",
  "problem_url": "https://codeforces.com/problemset/problem/71/A",
  "problem_metadata": {
    "name": "Way Too Long Words",
    "tags": [
      "strings"
    ],
    "time_limit_ms": 1000,
    "memory_limit_kb": 262144
  },
  "problem_statement_html": "<div class=\"problem-statement\"><div class=\"header\"><div class=\"title\">A. Way Too Long Words</div><div class=\"time-limit\"><div class=\"property-title\">time limit per test</div>1 second</div><div class=\"memory-limit\"><div class=\"property-title\">memory limit per test</div>256 megabytes</div><div class=\"input-file input-standard\" style=\"font-weight: bold\"><div class=\"property-title\">input</div>stdin</div><div class=\"output-file output-standard\" style=\"font-weight: bold\"><div class=\"property-title\">output</div>stdout</div></div><div><p>Sometimes some words like \"<span class=\"tex-font-style-tt\">localization</span>\" or \"<span class=\"tex-font-style-tt\">internationalization</span>\" are so long that writing them many times in one text is quite tiresome.</p><p>Let's consider a word <span class=\"tex-font-style-it\">too long</span>, if its length is <span class=\"tex-font-style-bf\">strictly more</span> than <span class=\"tex-span\">10</span> characters. All too long words should be replaced with a special abbreviation.</p><p>This abbreviation is made like this: we write down the first and the last letter of a word and between them we write the number of letters between the first and the last letters. That number is in decimal system and doesn't contain any leading zeroes.</p><p>Thus, \"<span class=\"tex-font-style-tt\">localization</span>\" will be spelt as \"<span class=\"tex-font-style-tt\">l10n</span>\", and \"<span class=\"tex-font-style-tt\">internationalization</span>\u00bb will be spelt as \"<span class=\"tex-font-style-tt\">i18n</span>\".</p><p>You are suggested to automatize the process of changing the words with abbreviations. At that all too long words should be replaced by the abbreviation and the words that are not too long should not undergo any changes.</p></div><div class=\"input-specification\"><div class=\"section-title\">Input</div><p>The first line contains an integer <span class=\"tex-span\"><i>n</i></span> (<span class=\"tex-span\">1\u2009\u2264\u2009<i>n</i>\u2009\u2264\u2009100</span>). Each of the following <span class=\"tex-span\"><i>n</i></span> lines contains one word. All the words consist of lowercase Latin letters and possess the lengths of from <span class=\"tex-span\">1</span> to <span class=\"tex-span\">100</span> characters.</p></div><div class=\"output-specification\"><div class=\"section-title\">Output</div><p>Print <span class=\"tex-span\"><i>n</i></span> lines. The <span class=\"tex-span\"><i>i</i></span>-th line should contain the result of replacing of the <span class=\"tex-span\"><i>i</i></span>-th word from the input data.</p></div><div class=\"sample-tests\"><div class=\"section-title\">Examples</div><div class=\"sample-test\"><div class=\"input\"><div class=\"title\">Input<div class=\"input-output-copier\" data-clipboard-target=\"#id0036618126666608464\" id=\"id0049122713937151274\" title=\"Copy\">Copy</div></div><pre id=\"id0036618126666608464\">4<br/>word<br/>localization<br/>internationalization<br/>pneumonoultramicroscopicsilicovolcanoconiosis<br/></pre></div><div class=\"output\"><div class=\"title\">Output<div class=\"input-output-copier\" data-clipboard-target=\"#id006783379976868567\" id=\"id0018473958951028768\" title=\"Copy\">Copy</div></div><pre id=\"id006783379976868567\">word<br/>l10n<br/>i18n<br/>p43s<br/></pre></div></div></div></div>",
  "pretests": [
    {
      "input": "4\nword\nlocalization\ninternationalization\npneumonoultramicroscopicsilicovolcanoconiosis",
      "output": "word\nl10n\ni18n\np43s"
    },
    {
      "input": "5\nabcdefgh\nabcdefghi\nabcdefghij\nabcdefghijk\nabcdefghijklm",
      "output": "abcdefgh\nabcdefghi\nabcdefghij\na9k\na11m"
    },
    {
      "input": "3\nnjfngnrurunrgunrunvurn\njfvnjfdnvjdbfvsbdubruvbubvkdb\nksdnvidnviudbvibd",
      "output": "n20n\nj27b\nk15d"
    },
    {
      "input": "1\ntcyctkktcctrcyvbyiuhihhhgyvyvyvyvjvytchjckt",
      "output": "t41t"
    },
    {
      "input": "24\nyou\nare\nregistered\nfor\npractice\nyou\ncan\nsolve\nproblems\nunofficially\nresults\ncan\nbe\nfound\nin\nthe\ncontest\nstatus\nand\nin\nthe\nbottom\nof\nstandings",
      "output": "you\nare\nregistered\nfor\npractice\nyou\ncan\nsolve\nproblems\nu10y\nresults\ncan\nbe\nfound\nin\nthe\ncontest\nstatus\nand\nin\nthe\nbottom\nof\nstandings"
    },
    {
      "input": "1\na",
      "output": "a"
    },
    {
      "input": "26\na\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk\nl\nm\nn\no\np\nq\nr\ns\nt\nu\nv\nw\nx\ny\nz",
      "output": "a\nb\nc\nd\ne\nf\ng\nh\ni\nj\nk\nl\nm\nn\no\np\nq\nr\ns\nt\nu\nv\nw\nx\ny\nz"
    },
    {
      "input": "1\nabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghijabcdefghij",
      "output": "a98j"
    },
    {
      "input": "10\ngyartjdxxlcl\nfzsck\nuidwu\nxbymclornemdmtj\nilppyoapitawgje\ncibzc\ndrgbeu\nhezplmsdekhhbo\nfeuzlrimbqbytdu\nkgdco",
      "output": "g10l\nfzsck\nuidwu\nx13j\ni13e\ncibzc\ndrgbeu\nh12o\nf13u\nkgdco"
    },
    {
      "input": "20\nlkpmx\nkovxmxorlgwaomlswjxlpnbvltfv\nhykasjxqyjrmybejnmeumzha\ntuevlumpqbbhbww\nqgqsphvrmupxxc\ntrissbaf\nqfgrlinkzvzqdryckaizutd\nzzqtoaxkvwoscyx\noswytrlnhpjvvnwookx\nlpuzqgec\ngyzqfwxggtvpjhzmzmdw\nrlxjgmvdftvrmvbdwudra\nvsntnjpepnvdaxiporggmglhagv\nxlvcqkqgcrbgtgglj\nlyxwxbiszyhlsrgzeedzprbmcpduvq\nyrmqqvrkqskqukzqrwukpsifgtdc\nxpuohcsjhhuhvr\nvvlfrlxpvqejngwrbfbpmqeirxlw\nsvmasocxdvadmaxtrpakysmeaympy\nyuflqboqfdt",
      "output": "lkpmx\nk26v\nh22a\nt13w\nq12c\ntrissbaf\nq21d\nz13x\no17x\nlpuzqgec\ng18w\nr19a\nv25v\nx15j\nl28q\ny26c\nx12r\nv26w\ns27y\ny9t"
    },
    {
      "input": "50\nyrjgqpycjomtrvtjbdjkfowjcqotocumrywnveocghtakthfexjitawazbexahopsfnltblsxrfuikmvrymi\nupotnopydemidaikmruvsahrfxhsuaaqdwumlymnfmmddkizzhukhy\nxqbomkygmudsiubderfosivskwdzvgikmsendtrrhhbccbmkvyeakliwakzohaephhl\nsuyccsofjnvjsixiddmtpuwxolodomtxojodlrmaopuffomlydrnxwgvnlymdsxepixsmmdzibpmukj\nqkiqsawnnlqctpibhyevsrlbpcclwmfvqyulotuvladwgjeworhlvozmwqesfclkwgfjaogdlbnkgcuayryzpsxp\nwfvvqhwtufohfzqsjoeqyrykenxkimbhgxljobaoplaxozvblykenscpkkuskvyyjgnoyojxlquzzxcsc\nsencqemgevhqgpxlntuwlbhmusldewgcobyemfefjh...",
      "output": "y82i\nu52y\nx65l\ns77j\nq86p\nw79c\ns49a\nq82k\nl80h\nv61s\nz63z\nz79x\nd81y\nu70j\nx78u\nn90x\ne59u\ne57o\nk61t\nx48k\nj72o\nv83t\nm85i\nu67r\nk60b\nr82b\ng49e\nt94l\nx83m\nx87w\ns77y\nj74a\np73t\na54r\nx54v\nt83q\na75a\nt86z\ns59y\nu64w\nt83b\na83v\na67w\ny84u\nv59t\nd81o\ng64e\nt61f\nn80w\ng56x"
    },
    {
      "input": "100\nyolunepgtmqshrounbdfdkijcpnflohkyosnsstjxnzwtaqbel\ncdbrfslhjwzscsxwgyexewnotocjvdkzjrzcyoydlwxcqbbvyqas\nntxwuxivdlpcstoypxadpjagrdfwcsftrqmmwucnpasjqpmzfmtiamnsuahiwuvtnntjsp\nurpqvhxoptmvuciyocdmywabfojyr\necnnxctltbisidjfguwwcapyicjwfikfdioebzpezcpoptwfnsqjrertonuuzzrducmquztzesfm\nilqxghkdyyxhghxwtpdzlxhskcdjaudkguk\ntalrxluwobnhqwrerehocgsuyoqonmifexblphvjeinvmavvpdwz\npfihtxhzsjthefffkgnoggujmgwvwaakrdswrhwrtcugt\nyeavjjiazkeyvprnxtktgogtvrapeiikxacdxdjmwlgtgrpdwkshdmznbvlmrlnblxygo\nwbqmfvxtrq...",
      "output": "y48l\nc50s\nn68p\nu27r\ne74m\ni33k\nt50z\np43t\ny67o\nw36u\no27u\nd22s\nf37m\ne82u\no37d\nx65t\nt32t\nz86w\nk40y\ng82q\nw67e\nt53m\ni71t\ny66s\ng40y\nv86n\np29g\nr52i\nn22r\nh87r\nn70m\nn61u\nk33l\nw88o\nl24k\nt59m\ne50f\nh57r\np67x\nq36z\ny71k\na60w\nj57q\nd30v\nt68o\ns25w\na80d\ny80u\nj27a\nc29n\nr44w\nc61c\nc19o\ni81m\nj69g\nv31a\nu30k\nz75b\ng42f\nt62e\nx58r\nq88b\ne40c\ni24t\nt50d\nj61r\nz25x\nw83y\nj49p\nx29d\nw80g\ni23o\nt55k\nc44x\na68i\nb81a\ng68z\nx61v\nj34s\nk63v\nh75z\no62n\nu67t\np21t\nw40z\nv..."
    },
    {
      "input": "100\nkezjrqolykktwvetqcldahyyyujxofzwjtosmzeicrbuaceimvzavbuzwttvxlrlowudhwnwojlnkgbjnmvodfdpglynlppqqcld\nzhuaejetjavgxvvreoqhjgugxrmgsklcvbpqfnvxgcyujofyddjeasxeaipchvtonlmecqyaufqoiyigqdxxlocvqxgtykbhlzvq\nfbfdyusznkzbnijokjyegwkcrvuxuskscpuiunjhmkywsnxpoxpchpbjgwsjgisvzejeavoltdrjvadrsmuyedgwkjiljpfolgjf\nhpwladutfouhnwkwvkvrmdpookgamsazsizagwdrhhsroxicornvnszekbcpkmwboajfgispffeunusycdeqlwkpnbxieygyjhdr\nedazowchpygyopadcxlcysjuaxnsrqeumtpcpxdpckfkiwovfctvvkioabvokvvrgfafhybncoxdbmmjnkdhtqcirydjyrnkcd...",
      "output": "k98d\nz98q\nf98f\nh98r\ne98a\no98s\nm98y\ne98v\np98i\ny98m\nj98u\na98d\nx98h\nc98r\ny98x\nd98c\ng98v\ni98v\na98d\ni98i\nk98b\nf98a\nw98j\ni98g\nq98t\nb98x\nb98a\nk98p\nw98l\nc98b\nf98m\nx98k\nx98d\na98e\np98s\na98a\ng98y\nj98k\nq98s\ny98i\nl98u\nj98u\nm98w\ng98u\ni98m\nm98t\nx98d\nq98c\ni98x\ni98d\nk98a\nc98c\nq98r\nh98m\nx98s\nz98s\nb98m\nc98l\nr98w\nn98i\nh98a\ny98d\nn98r\nw98c\nn98e\nx98i\nk98c\ng98s\no98c\nl98b\nf98v\np98l\no98d\nl98l\no98x\ny98i\nk98y\nm98x\nn98p\ns98m\ne98e\nf98n\nr98c\nm98g\nj98b\no..."
    },
    {
      "input": "100\nksypbdyjfrugidxbnjomeeufwwmwxnkvobaumflbcqastndtbuhhlgthgfjsgnqzpzbmtshqiiorhpnswsnwvjixtawjolmsejd\ngcholsavjvuisajckjupsyickxxmgaxnkrbzwyszcogqzkhcnruqauvszgachngijptowhteboixdtfoclsnjxpdwikpbfgep\nvaolfeyqhdavhsuilgwiillsgwqlxgtcauxogmoigixpffjqcaibubmtfdvcacffukrlwkmawzziiszhafjornzjxkugpffhoiv\npiykajezovdrytyaplvgnqzscfkebzkpwrqstlhffsvfyccjfubkqurcpskkcqadjtyoddutvzfvzyqvxvgpinfpujbpunhnm\nawzpqcybxokjnqtiitufqfrqcrjlkpbfrkuqwdfrsggedbxphcskipgsxisuxnmbloebtfnjideueebrvyyxaeqjarfmokeybmkh\nnutn...",
      "output": "k97d\ng95p\nv97v\np95m\na98h\nn93b\ng93k\nx95v\no98h\nx97y\nb98q\nv94a\ns95n\nb94g\nw98u\na95u\nj93y\nk98d\nn93s\nl98f\ny95v\nx94t\nh98c\nn95k\nh96z\nw93y\nr93j\na94p\no98r\nw93j\ni93o\nl96l\no94h\nb96n\nw97l\ne96o\nh95w\no94c\ny94o\nc96e\ni98q\ne94n\ng96l\nm96m\np93v\nt97k\nr97a\na93d\np95q\nx94m\ny94n\nr95t\nu97r\nq97h\ny95l\nx95a\nc96w\nk98b\nz93g\ng98f\nd98x\nq98v\no98l\na94u\nw95h\nx98i\nz94o\nu95g\ni96n\nz93s\ne96n\nt93l\nt97a\ne97t\nd95u\nk97m\ni94g\nw96q\nx97w\nt95p\no93u\nw93b\nv95s\ng96l\nd95i\nk..."
    },
    {
      "input": "100\nnprsotflzetfunpggctsnfjwukywklrslkzzubgbgodmleljoyhpvjovoxnngsrhunixnbfpwufvvbekuxzmemobotdnpdy\nrbvvdbhdjbsghnkzwyqrpilhycepcbonavyjuisgbloebybvnqkdmkjgtyevwgsihpthhgpbnnjbzepcflvpkhnfxsn\nkprlqdgthhlrzniorkppagehifilxpmuzlqjtesbcpxerzbgejwfpblvvyzhyxjebyhkokvzaezwnwipvhndps\nrglrodykudonvkhpznevydzicuzwmctzfuhibwgmewyxinqproqvyccjizomhvzzykvbuocxkfrhoxif\nijkuqdxjoicrkxcxevtwnrkyjdqpkvbdffsybzplclavobmaxpoqpxfqyfhegxwpxspcbilwwqdoxqkaesvjyseev\nuxqxqqkgcrkodeyoghaqsenzhpwneqtiiaczlpffmvuociwptlglgmv...",
      "output": "n93y\nr89n\nk84s\nr78f\ni87v\nu72u\nn68l\nx90g\nu76k\nv83m\ny82h\nk79k\nm80m\nr72u\ni84r\nb90l\nx94p\nc73r\nz89w\nr83v\nb95k\nz93u\ne92h\nt82o\nt74j\nw88d\nk79b\nr80y\nn87w\nj92q\ny70g\nd89v\na78h\nj68m\nv70n\np74r\nq76c\nj72p\ne80a\nw85z\nv87v\nj71h\nq93z\nu78b\nz84c\nn80f\nn86a\nk70k\nc97d\nx76j\ns90t\ne92q\nw72y\nh86y\no82h\ni72f\nk94l\nr96t\nd71c\nh78v\nb86f\nn75j\no81o\nu68i\nn78j\na70m\nc96i\nd91m\nx92f\ne73h\nw74u\nz79d\nn90u\nj86p\nf85k\no90j\nf76i\ni71j\nu96w\ng68k\ne83p\nt90z\ny83l\nw70l\ni89g\nn..."
    },
    {
      "input": "100\nm\nz\ns\nv\nd\nr\nv\ny\ny\ne\np\nt\nc\na\nn\nm\np\ng\ni\nj\nc\na\nb\nq\ne\nn\nv\no\nk\nx\nf\ni\nl\na\nq\nr\nu\nb\ns\nl\nc\nl\ne\nv\nj\nm\nx\nb\na\nq\nb\na\nf\nj\nv\nm\nq\nc\nt\nt\nn\nx\no\ny\nr\nu\nh\nm\nj\np\nj\nq\nz\ns\nj\no\ng\nc\nm\nn\no\nm\nr\no\ns\nt\nh\nr\np\nk\nb\nz\ng\no\nc\nc\nz\nz\ng\nr",
      "output": "m\nz\ns\nv\nd\nr\nv\ny\ny\ne\np\nt\nc\na\nn\nm\np\ng\ni\nj\nc\na\nb\nq\ne\nn\nv\no\nk\nx\nf\ni\nl\na\nq\nr\nu\nb\ns\nl\nc\nl\ne\nv\nj\nm\nx\nb\na\nq\nb\na\nf\nj\nv\nm\nq\nc\nt\nt\nn\nx\no\ny\nr\nu\nh\nm\nj\np\nj\nq\nz\ns\nj\no\ng\nc\nm\nn\no\nm\nr\no\ns\nt\nh\nr\np\nk\nb\nz\ng\no\nc\nc\nz\nz\ng\nr"
    },
    {
      "input": "100\nkrntmzhsruy\nftalxlmuc\ncozylrccxw\ndqlagguvhl\ncuocnvmvub\nxdzkuffnw\nijmxnkleicb\nrxjhxajhts\nzplvyiotwa\nuivwolgvl\nqlhjhaaxta\njpnuseneupm\nupzdpwbes\ntafwwszgtu\nsefoifnqip\nvmgpttdis\nnqmcuhhfunqi\nqvzrguvbdfra\nbcndjfdae\niihzyeyzertt\nqqxnprqtqc\nrbufkbbitlv\nrzlynunufwe\nvopnpdkwx\nsjomcujlgo\nrbcbzwbkbg\nnpyarzhwzpdo\noyrefcuimgvw\nxgudhpoedo\nbcxyqaybcpx\nndftxkfssdk\nhlvqyayxifb\nymnrfapuh\nncssyphac\nwysvqqbfz\nleqyrcadzo\nqyeymnydtcz\nyzwmynothdp\nnntkaihetkrk\nbhwhpaixsv\nvmuzllamj\numq...",
      "output": "k9y\nftalxlmuc\ncozylrccxw\ndqlagguvhl\ncuocnvmvub\nxdzkuffnw\ni9b\nrxjhxajhts\nzplvyiotwa\nuivwolgvl\nqlhjhaaxta\nj9m\nupzdpwbes\ntafwwszgtu\nsefoifnqip\nvmgpttdis\nn10i\nq10a\nbcndjfdae\ni10t\nqqxnprqtqc\nr9v\nr9e\nvopnpdkwx\nsjomcujlgo\nrbcbzwbkbg\nn10o\no10w\nxgudhpoedo\nb9x\nn9k\nh9b\nymnrfapuh\nncssyphac\nwysvqqbfz\nleqyrcadzo\nq9z\ny9p\nn10k\nbhwhpaixsv\nvmuzllamj\nu10e\ndjppfglew\ng9n\nzsxwrgtoc\ndkxebftrcu\ny9w\nk10n\nl10e\ntkahmqqnz\nirfdhmmkoo\nk10t\njhkpqloxg\nmjbbzlwlq\nq9q\na9c\nb9c\nylobxqnq..."
    },
    {
      "input": "100\nptigxyytcjldwhnnrzozkylyplxnftyppkbyuurgcapsbiwnmudmuzyeuwmbhldlo\nhadsqjnibxjmlogohrjlnroqaownnwsnxqcuzpywqaobdlfinttzwgwjygyhzfbz\nxjyesazizserkqwxgietuutmmzsghpzjjqxozmppxjidahgpskuyrqlb\nbelyjrwwhso\nnlyhqrxinnkjbyjo\nqmgltebmckerjreqroutjwexdwcllwqneccncxvtwt\nazxjylritlzfkmsxtxujejepmqleepcgdrmdvjpmezibveamwnoshphpy\nznurjkeibyidlvhxutrromsnvwfcaykylfxswfldkxfutfarcyjzhpgkvkrdqpgstemyfhnlkfjumxlaqfuumdwc\noagcwgiwlvomlqqsjsqqgkcanzlpt\nrafuzheef\njjklprlgtvbzfeqpijsgrzaibxidheecksoltjdfkvwqeoxun...",
      "output": "p63o\nh62z\nx54b\nb9o\nn14o\nq40t\na55y\nz86c\no27t\nrafuzheef\nj66e\nw61w\nn61u\ni91j\nk55k\nx55w\nz57d\nr33n\ny95j\ng92a\ng68e\nk18h\na27v\nz37w\np52q\nrlqjwwl\nk44z\nw52f\nc47z\nh45o\nv16m\nm20n\nx\nk91d\ne57b\np36u\nz40u\nf91w\nf60y\nv86w\ng26i\nb95h\nj81t\nd86x\nolkh\nh26q\ne55z\nc86v\nz78v\nu64r\nq86x\np87x\nv63z\nr20g\ni47d\na16e\nl86x\nc52p\nv96b\ng67x\ny87a\nkubrb\nr66t\ne89j\nlo\nw81g\ngfzeqs\nn90h\nh60r\noityxkv\nr\ns72e\nr27y\nv71f\nw20j\nn69g\no90i\nltkpauqvzz\nj48g\na44l\nw32j\nz48t\nq37p\nq6..."
    },
    {
      "input": "100\nnaasfslspkeegohsismncfdpwepkpzpmsmmsabbhxsogbkeqpchiswvhawncoyhhkbvtbxwregkwt\nylsrptkpkqvlpxqztmwhouokcmwmvtgkrksut\nnwoceaqyjmnhtbewispyrnjqmgearwxvfrfbbpxajbmahopwliihmepv\njtpirzevpytrljsxbxfrgptpurjnxopulatkluerdqwfxyxn\nnebkykkwipvvoqjscifzdubddhrtbokrlfnhrmmvfdcvyvodvaiarwtxhywklwlcnitjeywsxskrv\ncrzhngcwmmnwoqoaznfpzzztthuqt\nmmueebdobtkcsjltrdutbsafbijgodbwycwe\njohhvrhkzxbzugdebwhjobyuwghdbvnkqchgezcoxyugfndlambkhqweljoxqfcrqsjrrsitnlcjztzrsnp\negeqfnslewezcunbhzzgkahvgoachyrklymvxwvqsbtwhyx...",
      "output": "n75t\ny35t\nn54v\nj46n\nn75v\nc27t\nm34e\nj81p\ne98i\nc98k\nl53p\nl34m\no77i\nh24i\nr30l\nl19e\nx39a\nz34m\nx41q\na94f\nd66w\nw39x\nw83z\nm67i\nr66v\ni57j\nl92p\nq38e\ng96a\ng84h\nlgzgyex\nu59k\nb36q\ns31a\nz74e\nf91m\nl13w\nb48v\nc76c\nm25q\njoeil\nq62d\nz13j\nf45w\nq29x\nk93x\ng56r\nd23r\nj27z\nh69j\nw73f\nz24b\nn96z\nf87j\ne10v\nq30h\ns66p\nbhk\ni16a\nx51g\ne11m\nbgtshadywc\nv48i\nx80z\nu36j\ne57t\nw32s\nq97o\no92s\nd80a\nt38s\nb33h\nl53g\nc70i\ny28s\nn30y\nl12o\ny57c\nn39o\nc80d\ny84v\nj97n\nl80d\nh84v..."
    },
    {
      "input": "100\nljtenmwrekyeowdaxkkztmvgdwhhaffkupxngjljrknudlmrthlfrvtlexodwjmbhkjoydabwbuvdjjiewyvmtipc\negloaaxcewbcfixacmyuiiehaxfufwkthrwoyljdmtjmaeizifhjoqswylceogkkhotkvqycujgsbqmvnvwmjgh\nlpeizyslrvuyjmcwjqyyupqlezxfeeh\neyglycfdloswvgpuoqdgxacanoxbhmmtmmpwjzvkbbgjaohqqwxqqufehihusvhorwsxwmpksdipokjbeqqrhfzaagympofjgh\nklcwsxkaalpegrejf\nihknehlqlqlrdatnwsllidnrhdviogiskwxeaqrvsvphcdexoez\nzjmsahrkxrjgmewsedzcelvyhcexhwjlpxzcqgnifraqnblezaejroivqrzkvcglwhvnasvlvxyzuegxdnugwejzxbvf\nfhmdzwacbwjgnxihwxnfpnxesfd...",
      "output": "l87c\ne85h\nl29h\ne96h\nk15f\ni49z\nz90f\nf53r\nv28x\nk15c\ne75y\nf53f\nw65n\nv69m\nw55d\ne56r\nf93f\nz50r\nb19m\norifaapio\ne76e\ne13b\np20o\ng88h\nx46k\ne81r\nqkxobz\ng47b\nx45f\nm53i\np13h\nq87k\nh55d\ny25d\nzmbfvlhn\ntpftnjar\nf77l\nt42a\ns24d\nj75m\np15v\nq15y\nu69k\nu53s\nb10r\nd39a\np32h\nb83u\nw12c\nl64u\nc46u\nx72i\nl\nb81f\ni68i\nz28n\ne16s\np67g\no17k\nl9b\no65n\nd71a\np17a\nn12h\nb16q\nn30l\nqnyhwen\ns15e\nor\nl28r\ni77f\nr83j\ngp\ng76h\nk85l\na73e\nn45z\nb53r\nm15g\nd14l\nw69x\nl11d\nv95y\nu52..."
    }
  ],
  "reference_solution": {
    "submission_id": 369912941,
    "submission_url": "https://codeforces.com/contest/71/submission/369912941",
    "author_handle": "Amr_Arabi",
    "author_rating": null,
    "language": "C++23 (GCC 14-64, msys2)",
    "code": "#include <bits/stdc++.h>\nusing namespace std;\nint main()\n{\n    int t;\n    cin>>t;\nwhile (t--)\n{\n    string s;\n    cin >>s;\n    if(s.size()<=10)\n    {\n        cout <<s<<endl;\n    }\n    else \n    {\n        int mid=s.size()-2;\n         s.erase(1,mid);\n        s.insert(1,to_string(mid));\n        cout <<s<<endl;\n     }\n}\n }"
  },
  "verified_pseudocode": "// Time: O(N * L_max), where N is the number of words and L_max is the maximum word length.\n// Space: O(L_max) to store the current word.\n\nFUNCTION solve():\n  READ integer N\n  FOR i FROM 1 TO N:\n    READ string word\n    LET length = LENGTH(word)\n    IF length > 10 THEN\n      PRINT word[0] + TO_STRING(length - 2) + word[length - 1]\n    ELSE\n      PRINT word\n    PRINT newline\n\n// Main execution\nsolve()",
  "verified_solution_code": "#include <bits/stdc++.h>\nusing namespace std;\n\nstring abbreviateWord(string word) {\n  if (word.length() > 10) {\n    return word[0] + to_string(word.length() - 2) + word[word.length() - 1];\n  } else {\n    return word;\n  }\n}\n\nvoid solve() {\n  int N;\n  cin >> N;\n  for (int i = 0; i < N; i++) {\n    string word;\n    cin >> word;\n    string abbreviatedWord = abbreviateWord(word);\n    cout << abbreviatedWord << endl;\n  }\n}\n\nint main() {\n  ios_base::sync_with_stdio(false);\n  cin.tie(NULL);\n  solve();\n  return 0;\n}",
  "code_quality_analysis": {
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {
      "oracle_0": {
        "rating": "Excellent",
        "justification": "This solution correctly implements the problem's logic. It reads the number of test cases, then iterates through each word. For words longer than 10 characters, it constructs the abbreviation using the first character, the length minus 2, and the last character. Otherwise, it prints the word as-is. The time complexity is O(L) per word (where L is the word length) for reading and processing, making it O(N*L_max) total, which is optimal. Space complexity is O(L_max) to store the current word, also optimal. It handles all stated constraints and edge cases properly."
      }
    }
  }
}
```

