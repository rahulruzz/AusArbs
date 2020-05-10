# ------------------------------------------------------------------

import numpy as np
from fractions import Fraction

from webscraping.website import CWebsite
from util.message import message
import util.utilities as ut
from templates.HTML_template_elements import make_html

# ------------------------------------------------------------------

DEFAULT_LINK_ATTR_NAME = "href"
ODDSCHECKER_HOME = "https://www.odds.com.au/"

# ------------------------------------------------------------------

BET_AMOUNT = 100
INCLUDE_INPLAY = False

MIN_OPP = 1.03
MAX_OPP = 1.2
DISALLOWED_MARKETS = [
    "Half Time Winning Margin",
    "To Score 2 Or More Goals",
    "To Score A Hat-Trick.",
    "Last Goalscorer",
    "To Score 3+ Goals",
    "To Score 4+ Goals",
    "Score After 6 Games",
    "To Win Set 1 And Win",
    "Not To Win A Set",
    "Set 1 Score Groups",
    "Score After 2 Games"
]


# ------------------------------------------------------------------

class CWebCrawler(object):
    """
    Contains all the functionality for finding arb opps on Oddschecker.
    """

    def __init__(self, name="Oddschecker Web Crawler"):
        self.m_name = name
        self.all_results = []
        self.m_homepage = CWebsite(ODDSCHECKER_HOME, ODDSCHECKER_HOME, name="oddschecker_home")

    def run(self):
        # Grab all sports
        sport_specific_home_tags = self.m_homepage.getClasses(["sport-menu__link"])
        for sport_tag in sport_specific_home_tags:
            if not sport_tag.hasAttr(DEFAULT_LINK_ATTR_NAME):
                continue
            message.logDebug("Examining " + sport_tag.getName().strip() + " arbitrage opportunities.")

            try:
                # Form the link
                full_sport_link = ODDSCHECKER_HOME + sport_tag.getAttr(DEFAULT_LINK_ATTR_NAME)
                # Create the website object
                sport_website = CWebsite(full_sport_link, ODDSCHECKER_HOME, name=sport_tag.getName())
                # Website object successfully created. Check the sport's leagues
                check_leagues_for_sport(sport_website)
            except:
                message.logWarning("Unable to load web page, skipping to next sport")
                pass


def check_leagues_for_sport(sport_website):
    # Grab all leagues for current sport
    league_tags = sport_website.getClasses(["league-component"])
    for league_tag in league_tags:
        if not league_tag.hasAttr(DEFAULT_LINK_ATTR_NAME):
            continue
        league_name = league_tag.getName()
        message.logDebug("Examining league" + league_name)

        try:
            # Form the link for the league
            league_link = ODDSCHECKER_HOME + league_tag.getAttr(DEFAULT_LINK_ATTR_NAME).strip("/")
            # Create the website object
            league_website = CWebsite(league_link, ODDSCHECKER_HOME, name=league_name)
            # Check all the games for current league
            check_games_for_league(league_website)
        except:
            message.logWarning("Unable to load league, skipping to next league")
            continue


def check_games_for_league(league_website):
    if not INCLUDE_INPLAY:
        # Disregard any games that are in play
        if len(league_website.getClasses("no-arrow in-play")) > 0:
            message.logDebug("Game is in play, skipping.")
            return

    try:
        game_tags = league_website.getClasses("meeting head-to-head draw")
    except:
        message.logWarning("Unable to load market tags, skipping to next match")
        return

    game_tags = [m for m in game_tags if m.getName() not in DISALLOWED_MARKETS]
    game_tags.reverse()
    for game_tag in game_tags:

        message.logDebug("Considering market: " + game_tag.getName() + ".")

        try:
            game_webpage = CWebsite(
                sport_home_webpage.getHomeURL() + game_tag.getAttr(DEFAULT_LINK_ATTR_NAME),
                ODDSCHECKER_HOME, name=game_name + ": " + game_tag.getName())
        except:
            message.logWarning("Unable to load webpage, skipping to next market")
            continue

        self._check_website(game_webpage)


def _check_website(self, website, supress=False, verify=False):
    """
    Checks one website for arb opps.
    """
    if isinstance(website, str):
        website = CWebsite(website, ODDSCHECKER_HOME, name=website)
    table_tags = website.getClasses("diff-row evTabRow bc")
    bet_names = [""] * len(table_tags)
    best_odds = np.zeros(len(table_tags))
    best_odds_ind = [0] * len(table_tags)
    for tnum, table in enumerate(table_tags):
        for tchild, table_elem in enumerate(table.getChildren()):
            if len(table_elem.getClasses("beta-sprite add-to-bet-basket")) == 1:
                name = table_elem.getClasses("beta-sprite add-to-bet-basket")[0].getAttr("data-name")
                if name is not None:
                    bet_names[tnum] = name
            if "wo-col" in table_elem.getClassName():
                break
            if table_elem.hasAttr("data-odig") and table_elem.hasAttr("data-o") and isinstance(
                    table_elem.getAttr("data-o"), (str, int)) \
                    and table_elem.getAttr("data-o") != "" and "np" not in table_elem.getClassName() \
                    and float(table_elem.getAttr("data-odig")) > best_odds[tnum]:
                best_odds[tnum] = float(table_elem.getAttr("data-odig"))
                best_odds_ind[tnum] = tchild

    if len(best_odds) > 1:
        if min(best_odds) > 0:
            bet_goodness = (1. / sum(1. / best_odds))

            if MIN_OPP < bet_goodness < MAX_OPP:

                # Find websites with best odds
                best_sites = []
                for best_odd_index in best_odds_ind:
                    best_odd_column = website.getClasses("eventTableHeader")[0].getChildren()[best_odd_index]
                    best_sites.append(best_odd_column.getChildren()[0].getChildren()[0].getAttr("title"))

                arb_opp = str((1. / sum(1. / best_odds)) * BET_AMOUNT - BET_AMOUNT)
                correct_bets = (BET_AMOUNT / best_odds) * (1 / sum(1. / best_odds))

                instructions = []
                for bet_num in range(len(correct_bets)):
                    odds = Fraction(best_odds[bet_num] - 1).limit_denominator(1000)
                    msg = "BET " + str(round(correct_bets[bet_num], 2)) + " on selection " + bet_names[
                        bet_num] + " on website " + \
                          best_sites[bet_num] + " at odds " + str(odds.numerator) + "/" + str(
                        odds.denominator) + "."
                    instructions.append(msg)

                self._processResult({
                    "Name": website.getName(),
                    "Arbitrage Opportunity": str(round(float(arb_opp), 2)),
                    "Link": website.getURL(),
                    "Instructions": instructions},
                    supress=supress,
                    verify=verify
                )
                return True
    return False


def _processResult(self, result, supress=False, verify=False):
    """
    Is run when a result is found.
    """
    self.all_results.append(result)
    if verify:
        self._check_results()
    name = result["Name"].split(":")
    if not supress:
        message.logResult("#------------------------------------------------------------------")
        message.logResult("ARBITRAGE OPPORTUNITY OF " + result["Arbitrage Opportunity"] + " FOUND!")
        message.logResult("GAME: " + name[0])
        message.logResult("MARKET: " + name[1])
        message.logResult("LINK: " + result["Link"])
        message.logResult("#------------------------------------------------------------------")
        for r in result["Instructions"]:
            message.logResult(r)
        message.logResult("#------------------------------------------------------------------")
    html = make_html(self.all_results)

    with open("results.html", "w") as file:
        file.write(html)

    # then beep
    if not supress:
        ut.beep('templates/ding.wav')


def _check_results(self):
    links = [r["Link"] for r in self.all_results]
    self.all_results = []
    for l in links:
        self._check_website(l, verify=True)


if __name__ == "__main__":
    go = CWebCrawler()
    go.run()
