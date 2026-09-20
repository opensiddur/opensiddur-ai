"""Read from printed 151–156 (IA n175–n180); no text after Shacharit."""
# Verse, printed commandment label (None continues the paragraph), Hebrew, English.
DECALOGUE = (
(1, '', 'וַיְדַבֵּר אֱלֹהִים אֵת כָּל הַדְּבָרִים הָאֵלֶּה, לֵאמֹר:', 'God spoke all these words, saying:'),
(2, 'א', 'אָנֹכִי יְהֹוָה אֱלֹהֶיךָ, אֲשֶׁר הוֹצֵאתִיךָ מֵאֶרֶץ מִצְרַיִם, מִבֵּית עֲבָדִים.', 'I am the Lord your God, who brought you out of the land of Egypt, out of the house of slavery.'),
(3, 'ב', 'לֹא יִהְיֶה לְךָ אֱלֹהִים אֲחֵרִים עַל פָּנָי.', 'You shall have no other gods beside me.'),
(4, None, 'לֹא תַעֲשֶׂה לְךָ פֶסֶל וְכָל תְּמוּנָה אֲשֶׁר בַּשָּׁמַיִם מִמַּעַל, וַאֲשֶׁר בָּאָרֶץ מִתָּחַת, וַאֲשֶׁר בַּמַּיִם מִתַּחַת לָאָרֶץ.', 'You shall not make for yourself any idols in the shape of anything that is in heaven above, or of that which is on the earth below, or of that which is in the water under the earth.'),
(5, None, 'לֹא תִשְׁתַּחֲוֶה לָהֶם וְלֹא תָעָבְדֵם, כִּי אָנֹכִי יְהֹוָה אֱלֹהֶיךָ אֵל קַנָּא, פֹּקֵד עֲוֹן אָבֹת עַל בָּנִים, עַל שִׁלֵּשִׁים וְעַל רִבֵּעִים, לְשֹׂנְאָי.', 'You shall not bow down to them nor worship them; for I, the Lord your God, am a jealous God, punishing children for the sins of their fathers, down to the third or fourth generation of those who hate me,'),
(6, None, 'וְעֹשֶׂה חֶסֶד לַאֲלָפִים, לְאֹהֲבַי וּלְשֹׁמְרֵי מִצְוֹתָי.', 'but showing kindness to the thousandth generation of those who love me and keep my commandments.'),
(7, 'ג', 'לֹא תִשָּׂא אֶת שֵׁם יְהֹוָה אֱלֹהֶיךָ לַשָּׁוְא, כִּי לֹא יְנַקֶּה יְהֹוָה אֵת אֲשֶׁר יִשָּׂא אֶת שְׁמוֹ לַשָּׁוְא.', 'You shall not utter the name of the Lord your God in vain; for the Lord will not hold guiltless anyone who utters his name in vain.'),
(8, 'ד', 'זָכוֹר אֶת יוֹם הַשַּׁבָּת לְקַדְּשׁוֹ.', 'Remember the Sabbath day to keep it holy.'),
(9, None, 'שֵׁשֶׁת יָמִים תַּעֲבֹד וְעָשִׂיתָ כָּל מְלַאכְתֶּךָ.', 'Six days you shall labor and do all your work;'),
(10, None, 'וְיוֹם הַשְּׁבִיעִי שַׁבָּת לַיהֹוָה אֱלֹהֶיךָ; לֹא תַעֲשֶׂה כָל מְלָאכָה, אַתָּה וּבִנְךָ וּבִתֶּךָ, עַבְדְּךָ וַאֲמָתְךָ וּבְהֶמְתֶּךָ, וְגֵרְךָ {pb:153}אֲשֶׁר בִּשְׁעָרֶיךָ.', 'but on the seventh day, which is a day of rest in honor of the Lord your God, you shall not do any work, neither you, nor your son, nor your daughter, nor your male or female servant, nor your cattle, nor the stranger who is {pb:154}within your gates;'),
(11, None, 'כִּי שֵׁשֶׁת יָמִים עָשָׂה יְהֹוָה אֶת הַשָּׁמַיִם וְאֶת הָאָרֶץ, אֶת הַיָּם, וְאֶת כָּל אֲשֶׁר בָּם, וַיָּנַח בַּיּוֹם הַשְּׁבִיעִי; עַל כֵּן בֵּרַךְ יְהֹוָה אֶת יוֹם הַשַּׁבָּת וַיְקַדְּשֵׁהוּ.', 'for in six days the Lord made the heavens, the earth, the sea, and all that they contain, and rested on the seventh day; therefore the Lord blessed the Sabbath day and hallowed it.'),
(12, 'ה', 'כַּבֵּד אֶת אָבִיךָ וְאֶת אִמֶּךָ, לְמַעַן יַאֲרִכוּן יָמֶיךָ עַל הָאֲדָמָה אֲשֶׁר יְהֹוָה אֱלֹהֶיךָ נֹתֵן לָךְ.', 'Honor your father and your mother, that you may live long in the land which the Lord your God is giving you.'),
(13, 'ו', 'לֹא תִרְצָח.', 'You shall not murder.'),
(14, 'ז', 'לֹא תִנְאָף.', 'You shall not commit adultery.'),
(15, 'ח', 'לֹא תִגְנֹב.', 'You shall not steal.'),
(16, 'ט', 'לֹא תַעֲנֶה בְרֵעֲךָ עֵד שָׁקֶר.', 'You shall not testify falsely against your neighbor.'),
(17, 'י', 'לֹא תַחְמֹד בֵּית רֵעֶךָ; לֹא תַחְמֹד אֵשֶׁת רֵעֶךָ, וְעַבְדּוֹ וַאֲמָתוֹ וְשׁוֹרוֹ וַחֲמֹרוֹ, וְכֹל אֲשֶׁר לְרֵעֶךָ.', 'You shall not covet your neighbor’s house; you shall not covet your neighbor’s wife, nor his servant, male or female, nor his ox, nor his ass, nor anything that belongs to your neighbor.'),
)

# Hebrew repeats the introductory formula in full for each principle.
BELIEVE = 'אֲנִי מַאֲמִין בֶּאֱמוּנָה שְׁלֵמָה '
CREATOR = 'שֶׁהַבּוֹרֵא, יִתְבָּרַךְ שְׁמוֹ, '
PRINCIPLES = (
('א', CREATOR + 'הוּא בוֹרֵא וּמַנְהִיג לְכָל הַבְּרוּאִים, וְהוּא לְבַדּוֹ עָשָׂה וְעוֹשֶׂה וְיַעֲשֶׂה לְכָל הַמַּעֲשִׂים.', 'I firmly believe that the Creator, blessed be his name, is the Creator and Ruler of all created beings, and that he alone has made, does make, and ever will make all things.'),
('ב', CREATOR + 'הוּא יָחִיד, וְאֵין יְחִידוּת כָּמוֹהוּ בְּשׁוּם פָּנִים, וְהוּא לְבַדּוֹ אֱלֹהֵינוּ, הָיָה, הֹוֶה, וְיִהְיֶה.', 'I firmly believe that the Creator, blessed be his name, is One; that there is no oneness in any form like his; and that he alone was, is, and ever will be our God.'),
('ג', CREATOR + 'אֵינוֹ גוּף, וְלֹא יַשִּׂיגוּהוּ מַשִּׂיגֵי הַגּוּף, וְאֵין לוֹ שׁוּם דִּמְיוֹן כְּלָל.', 'I firmly believe that the Creator, blessed be his name, is not corporeal; that no bodily accidents apply to him; and that there exists nothing whatever that resembles him.'),
('ד', CREATOR + 'הוּא רִאשׁוֹן וְהוּא אַחֲרוֹן.', 'I firmly believe that the Creator, blessed be his name, was the first and will be the last.'),
('ה', CREATOR + 'לוֹ לְבַדּוֹ רָאוּי לְהִתְפַּלֵּל, וְאֵין רָאוּי לְהִתְפַּלֵּל לְזוּלָתוֹ.', 'I firmly believe that the Creator, blessed be his name, is the only one to whom it is proper to address our prayers, and that we must not pray to anyone else.'),
('ו', 'שֶׁכָּל דִּבְרֵי נְבִיאִים אֱמֶת.', 'I firmly believe that all the words of the Prophets are true.'),
('ז', 'שֶׁנְּבוּאַת מֹשֶׁה רַבֵּנוּ, עָלָיו הַשָּׁלוֹם, הָיְתָה אֲמִתִּית, וְשֶׁהוּא הָיָה אָב לַנְּבִיאִים, לַקּוֹדְמִים לְפָנָיו וְלַבָּאִים אַחֲרָיו.', 'I firmly believe that the prophecy of Moses our teacher, may he rest in peace, was true; and that he was the chief of the prophets, both of those who preceded and of those that followed him.'),
('ח', 'שֶׁכָּל הַתּוֹרָה הַמְּצוּיָה עַתָּה בְיָדֵינוּ, הִיא הַנְּתוּנָה לְמֹשֶׁה רַבֵּנוּ, עָלָיו הַשָּׁלוֹם.', 'I firmly believe that the whole Torah which we now possess is the same which was given to Moses our teacher, may he rest in peace.'),
('ט', 'שֶׁזֹּאת הַתּוֹרָה לֹא תְהִי מֻחֲלֶפֶת, וְלֹא תְהִי תּוֹרָה אַחֶרֶת מֵאֵת הַבּוֹרֵא, יִתְבָּרַךְ שְׁמוֹ.', 'I firmly believe that this Torah will not be changed, and that there will be no other Torah given by the Creator, blessed be his name.'),
('י', CREATOR + 'יוֹדֵעַ כָּל מַעֲשֵׂה בְנֵי אָדָם וְכָל מַחְשְׁבוֹתָם, שֶׁנֶּאֱמַר: {quote}הַיֹּצֵר יַחַד לִבָּם, הַמֵּבִין אֶל כָּל מַעֲשֵׂיהֶם.{/quote}', 'I firmly believe that the Creator, blessed be his name, knows all the actions and thoughts of human beings, as it is said: {quote}“It is he who fashions the hearts of them all, he who notes all their deeds.”{/quote}'),
('יא', CREATOR + 'גּוֹמֵל טוֹב לְשׁוֹמְרֵי מִצְוֹתָיו, וּמַעֲנִישׁ לְעוֹבְרֵי מִצְוֹתָיו.', 'I firmly believe that the Creator, blessed be his name, rewards those who keep his commands, and punishes those who transgress his commands.'),
('יב', 'בְּבִיאַת הַמָּשִׁיחַ; וְאַף עַל פִּי שֶׁיִּתְמַהְמֵהַּ, עִם כָּל זֶה אֲחַכֶּה לּוֹ בְּכָל יוֹם שֶׁיָּבֹא.', 'I firmly believe in the coming of Messiah; and although he may tarry, I daily wait for his coming.'),
('יג', 'שֶׁתִּהְיֶה תְּחִיַּת הַמֵּתִים בְּעֵת שֶׁיַּעֲלֶה רָצוֹן מֵאֵת הַבּוֹרֵא, יִתְבָּרַךְ שְׁמוֹ וְיִתְעַלֶּה זִכְרוֹ לָעַד וּלְנֵצַח נְצָחִים.', 'I firmly believe that there will be a revival of the dead at a time which will please the Creator, blessed and exalted be his name forever and ever.'),
)
HOPE = (
('לִישׁוּעָתְךָ קִוִּיתִי, יְיָ.', 'For thy salvation I hope, O Lord.'),
('קִוִּיתִי, יְיָ, לִישׁוּעָתְךָ.', 'I hope, O Lord, for thy salvation.'),
('יְיָ, לִישׁוּעָתְךָ קִוִּיתִי.', 'O Lord, for thy salvation I hope.'),
)
TARGUM = 'לְפֻרְקָנָךְ סַבֵּרִית, יְיָ. סַבֵּרִית, יְיָ, לְפֻרְקָנָךְ. יְיָ, לְפֻרְקָנָךְ סַבֵּרִית.'
