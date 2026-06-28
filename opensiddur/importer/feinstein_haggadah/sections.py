"""Haggadah section hierarchy and slug helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Literal

# Index nodes may contain section headings and body text as well as transclusions.
INDEX_CHILDREN: dict[str, list[str]] = {
    "index": ["pre_seder", "seder"],
    "pre_seder": ["bedikat_chametz", "biur_chametz", "eruv_tavshilin"],
    "seder": [
        "siman_maaseh_sedurim",
        "kadesh",
        "urechatz",
        "karpas",
        "yachatz",
        "magid",
        "rachtzah",
        "motzi_matzah",
        "maror",
        "korech",
        "shulchan_orech",
        "tzafun",
        "barech",
        "hallel",
        "nirtzah",
        "sefirat_haomer",
    ],
}

# h3 English title -> slug for top-level content sections (non-index).
H3_SLUGS: dict[str, str] = {
    "Search for Leaven": "bedikat_chametz",
    "Elimination of Leaven": "biur_chametz",
    "Mingling of Foods": "eruv_tavshilin",
    "Parts of the Seder": "siman_maaseh_sedurim",
    "Sanctification of the Day": "kadesh",
    "Preliminary Hand Washing": "urechatz",
    "Eating a Vegetable": "karpas",
    "Breaking the Middle Matzah": "yachatz",
    "Discussing the Exodus": "magid",
    "Hand-Washing before the Meal": "rachtzah",
    "Eating the Matzah": "motzi_matzah",
    "Eating the Bitter Herb": "maror",
    "Eating the “Hillel Sandwich”": "korech",
    "Eating the “Hillel Sandwich&#8221;": "korech",
    "Eating a festive meal": "shulchan_orech",
    "Eating the Afikoman": "tzafun",
    "Blessing After Meals": "barech",
    "Songs of Praise": "hallel",
    "Concluding Songs": "nirtzah",
    "Sefirat HaOmer": "sefirat_haomer",
}

# Explicit slugs for magid subsections (Hebrew first-line prefix -> slug).
MAGID_SUBSECTION_PREFIXES: list[tuple[str, str]] = [
    ("הָא לַחְמָא עַנְיָא", "ha_lachma_anya"),
    ("מַה נִשְׁתַּנָּה", "mah_nishtanah"),
    ("עֲבָדִים הָיִינוּ", "avadim_hayinu"),
    ("מַעֲשֶׂה", "maaseh_be_rabbi_eliezer"),
    ("אָמַר רַבִּי אֶלְעָזָר בֶּן עֲזַרְיָה", "amar_rabbi_elazar_ben_azariah"),
    ("בָּרוּךְ הַמָּקוֹם", "baruch_hamakom"),
    ("כְּנֶגֶד אַרְבָּעָה בָנִים", "arba_banim"),
    ("חָכָם מַה הוּא אוֹמֵר", "chacham"),
    ("רָשָׁע מַה הוּא אוֹמֵר", "rashaa"),
    ("תָּם מַה הוּא אוֹמֵר", "tam"),
    ("וְשֶׁאֵינוֹ יוֹדֵעַ לִשְׁאוֹל", "she_eino_yodea_lishol"),
    ("יָכוֹל מֵרֹאשׁ חֹדֶשׁ", "yachol_meros_hodesh"),
    ("מִתְּחִלָּה", "matchil_b_genut"),
    ("בָּרוּךְ שׁוֹמֵר", "baruch_shomer"),
    ("וְהִיא שֶׁעָמְדָה", "vehi_sheamda"),
    ("צֵא וּלְמַד", "arami_oved_avi"),
    ("וַיֵּ֣רֶד מִצְרַ֔יְמָה", "vayered_mitsraymah"),
    ("וַיָּ֥גׇר שָׁ֖ם", "vayagar_sham"),
    ("בִּמְתֵ֣י מְעָ֑ט", "bimtei_me_at"),
    ("וַֽיְהִי־שָׁ֕ם לְג֥וֹי גָּד֖וֹל", "vayehi_sham_le_goy_gadol"),
    ("עָצ֥וּם", "atzum"),
    ("וָרָֽב", "varav"),
    ("וַיָּרֵ֧עוּ אֹתָ֛נוּ הַמִּצְרִ֖ים וַיְעַנּ֑וּנוּ", "mitzrim_ra_v_inyu"),
    ("וַיָּרֵ֧עוּ אֹתָ֛נוּ הַמִּצְרִ֖ים", "mitzrim_ra"),
    ("וַיְעַנּ֑וּנוּ", "vay_inyunu"),
    ("וַיִּתְּנ֥וּ עָלֵ֖ינוּ עֲבֹדָ֥ה קָשָֽׁה", "avoda_kasha"),
    ("וַנִּצְעַ֕ק אֶל־יְהוָ֖ה", "vanitzak_hashem"),
    ("וַנִּצְעַ֕ק אֶל־יְהוָ֖ה אֱלֹהֵ֣י אֲבֹתֵ֑ינוּ", "vanitzak_elohai_avot"),
    ("וַיִּשְׁמַ֤ע יְהוָה֙", "vayishma_hashem"),
    ("וַיַּ֧רְא אֶת־עׇנְיֵ֛נוּ", "vayar_et_onyenu"),
    ("וְאֶת־עֲמָלֵ֖נוּ", "ve_et_amalenu"),
    ("וְאֶת־לַחֲצֵֽנוּ", "ve_et_lachatzenu"),
    ("וַיּוֹצִאֵ֤נוּ יְהוָה֙ מִמִּצְרַ֔יִם בְּיָ֤ד חֲזָקָה", "vayotzieinu_yad_chazaka"),
    ("וַיּוֹצִאֵ֤נוּ יְהוָה֙ מִמִּצְרַ֔יִם", "vayotzieinu_mimitzrayim"),
    ("וְעָבַרְתִּ֣י בְאֶֽרֶץ־מִצְרַיִם֮", "ve_avarti_b_eretz_mitzrayim"),
    ("בְּיָ֤ד חֲזָקָה֙", "b_yad_chazaka"),
    ("וּבִזְרֹ֣עַ נְטוּיָ֔ה", "u_vizroa_netuya"),
    ("וּבְמֹרָ֖א גָּדֹ֑ל", "u_v_mora_gadol"),
    ("וּבְאֹת֖וֹת", "u_votot"),
    ("וּבְמֹפְתִֽים", "u_v_moftim"),
    ("דָּבָר אַחֵר", "davar_acher"),
    ("אֵלּוּ עֶשֶׂר מַכּוֹת", "elu_eser_makot"),
    ("רַבִּי יְהוּדָה", "rabbi_yehuda_makot"),
    ("רַבִּי יוֹסֵי הַגְּלִילִי", "rabbi_yossi_hagalili"),
    ("רַבִּי אֱלִיעֶזֶר אוֹמֵר", "rabbi_eliezer_omar"),
    ("רַבִּי עֲקִיבָא אוֹמֵר", "rabbi_akiva_omar"),
    ("כַּמָּה מַעֲלוֹת טוֹבוֹת", "kama_maalot_tovot"),
    ("עַל אַחַת כַּמָּה וְכַמָּה", "al_achat_kamah"),
    ("רַבָּן גַּמְלִיאֵל הָיָה אוֹמֵר", "rabban_gamliel"),
    ("פֶּסַח", "pesach_mitzvah"),
    ("מַצָּה זוּ", "matzah_zu"),
    ("מָרוֹר זֶה", "maror_zeh"),
    ("בְּכָׇל דּוֹר וָדוֹר", "bechol_dor_vador"),
    ("לְפִיכָךְ", "lefikach"),
    ("הַ֥לֲלוּ יָ֨הּ", "halelu_yah"),
    ("בְּצֵ֣את יִ֭שְׂרָאֵ֖ל", "b_tzeis_yisrael"),
]

NIRTZAH_SUBSECTION_PREFIXES: list[tuple[str, str]] = [
    ("חֲסַל סִדּוּר פֶּסַח", "chasal_siddur_pesach"),
    ("וַיְהִי בַּחֲצִי הַלַּֽיְלָה", "it_happened_at_midnight"),
    ("וַאֲמַרְתֶּם זֶֽבַח פֶּֽסַח", "you_shall_say_pesach"),
    ("כִּי לוֹ נָאֶה", "ki_lo_na_eh"),
    ("אַדִּיר הוּא", "adir_hu"),
    ("אֶחָד מִי יוֹדֵעַ", "echad_mi_yodea"),
    ("חַד גַּדְיָא", "chad_gadya"),
]

INDEX_CHILDREN["magid"] = [slug for _, slug in MAGID_SUBSECTION_PREFIXES]
INDEX_CHILDREN["nirtzah"] = [slug for _, slug in NIRTZAH_SUBSECTION_PREFIXES]

INDEX_NODES = frozenset(INDEX_CHILDREN.keys())


@dataclass
class TextBlock:
    kind: Literal["head", "paragraph", "instruction"]
    hebrew: str = ""
    english: str = ""
    starts_paragraph: bool = False


@dataclass
class SectionContent:
    slug: str
    blocks: list[TextBlock] = field(default_factory=list)

    @property
    def hebrew_lines(self) -> list[str]:
        """Paragraph Hebrew text in order (for page-break alignment)."""
        return [block.hebrew for block in self.blocks if block.kind == "paragraph" and block.hebrew]

    @property
    def english_lines(self) -> list[str]:
        return [block.english for block in self.blocks if block.kind == "paragraph" and block.english]


def parent_index_slug(slug: str) -> str | None:
    for parent, children in INDEX_CHILDREN.items():
        if slug in children:
            return parent
    return None


def urn_for_section(slug: str, *, paragraph: int | None = None) -> str:
    if slug == "index":
        base = "urn:x-opensiddur:text:haggadah:haggadah"
    else:
        parent = parent_index_slug(slug)
        if parent in ("magid", "nirtzah"):
            base = f"urn:x-opensiddur:text:haggadah:{parent}/{slug}"
        else:
            base = f"urn:x-opensiddur:text:haggadah:{slug}"
    if paragraph is not None:
        return f"{base}/{paragraph}"
    return base


def iter_index_files() -> Iterator[str]:
    yield "index"
    for node in INDEX_NODES:
        if node != "index":
            yield node


def leaf_slugs() -> list[str]:
    leaves: list[str] = []
    for parent, children in INDEX_CHILDREN.items():
        for child in children:
            if child not in INDEX_NODES:
                leaves.append(child)
    return leaves


def document_order_slugs() -> list[str]:
    """Leaf section slugs in haggadah reading order (for PDF page alignment)."""
    order: list[str] = []

    def add_leaves(parent: str) -> None:
        for child in INDEX_CHILDREN[parent]:
            if child in INDEX_NODES:
                add_leaves(child)
            else:
                order.append(child)

    add_leaves("index")
    return order


def match_subsection_slug(
    first_line: str,
    prefixes: list[tuple[str, str]],
) -> str | None:
    for prefix, slug in prefixes:
        if first_line.startswith(prefix) or prefix in first_line:
            return slug
    return None
