"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

End-of-episode / Doom 2 texts + MAP30 cast (f_finale.prg).
"""

from __future__ import annotations

import os

import pygame

from .defs import HU_FONTEND, HU_FONTSTART, HU_FONTSIZE, SCREENHEIGHT, SCREENWIDTH
from .info import (
    FF_FRAMEMASK,
    MI_DEATHSTATE,
    MI_MELEESTATE,
    MI_MISSILESTATE,
    MI_SEESTATE,
    MOBJINFO,
    MT_BABY,
    MT_BRUISER,
    MT_CHAINGUY,
    MT_CYBORG,
    MT_FATSO,
    MT_HEAD,
    MT_KNIGHT,
    MT_PAIN,
    MT_PLAYER,
    MT_POSSESSED,
    MT_SERGEANT,
    MT_SHOTGUY,
    MT_SKULL,
    MT_SPIDER,
    MT_TROOP,
    MT_UNDEAD,
    MT_VILE,
    S_BOS2_ATK2,
    S_BOSS_ATK2,
    S_BSPI_ATK2,
    S_CPOS_ATK2,
    S_CPOS_ATK3,
    S_CPOS_ATK4,
    S_CYBER_ATK2,
    S_CYBER_ATK4,
    S_CYBER_ATK6,
    S_FATT_ATK2,
    S_FATT_ATK5,
    S_FATT_ATK8,
    S_HEAD_ATK2,
    S_NULL,
    S_PAIN_ATK3,
    S_PLAY_ATK1,
    S_POSS_ATK2,
    S_SARG_ATK2,
    S_SKEL_FIST2,
    S_SKEL_FIST4,
    S_SKEL_MISS2,
    S_SKULL_ATK2,
    S_SPID_ATK2,
    S_SPID_ATK3,
    S_SPOS_ATK2,
    S_TROO_ATK3,
    S_VILE_ATK2,
    SPRNAMES,
    STATES,
)
from .sprites import lookup_sprite
from .v_video import _u32, draw_patch, fill, patch_size

TEXTSPEED = 3
TEXTWAIT = 250
STAGE_TEXT = 0
STAGE_ART = 1
STAGE_CAST = 2

E1TEXT = (
    "Once you beat the big badasses and\n"
    "clean out the moon base you're supposed\n"
    "to win, aren't you? Aren't you? Where's\n"
    "your fat reward and ticket home? What\n"
    "the hell is this? It's not supposed to\n"
    "end this way!\n"
    "\n"
    "It stinks like rotten meat, but looks\n"
    "like the lost Deimos base.  Looks like\n"
    "you're stuck on The Shores of Hell.\n"
    "The only way out is through.\n"
    "\n"
    "To continue the DOOM experience, play\n"
    "The Shores of Hell and its amazing\n"
    "sequel, Inferno!\n"
)

E2TEXT = (
    "You've done it! The hideous cyber-\n"
    "demon lord that ruled the lost Deimos\n"
    "moon base has been slain and you\n"
    "are triumphant! But ... where are\n"
    "you? You clamber to the edge of the\n"
    "moon and look down to see the awful\n"
    "truth.\n"
    "\n"
    "Deimos floats above Hell itself!\n"
    "You've never heard of anyone escaping\n"
    "from Hell, but you'll make the bastards\n"
    "sorry they ever heard of you! Quickly,\n"
    "you rappel down to  the surface of\n"
    "Hell.\n"
    "\n"
    "Now, it's on to the final chapter of\n"
    "DOOM! -- Inferno.\n"
)

E3TEXT = (
    "The loathsome spiderdemon that\n"
    "masterminded the invasion of the moon\n"
    "bases and caused so much death has had\n"
    "its ass kicked for all time.\n"
    "\n"
    "A hidden doorway opens and you enter.\n"
    "You've proven too tough for Hell to\n"
    "contain, and now Hell at last plays\n"
    "fair -- for you emerge from the door\n"
    "to see the green fields of Earth!\n"
    "Home at last.\n"
    "\n"
    "You wonder what's been happening on\n"
    "Earth while you were battling evil\n"
    "unleashed. It's good that no Hell-\n"
    "spawn could have come through that\n"
    "door with you ...\n"
)

E4TEXT = (
    "the spider mastermind must have sent forth\n"
    "its legions of hellspawn before your\n"
    "final confrontation with that terrible\n"
    "beast from hell.  but you stepped forward\n"
    "and brought forth eternal damnation and\n"
    "suffering upon the horde as a true hero\n"
    "would in the face of something so evil.\n"
    "\n"
    "besides, someone was gonna pay for what\n"
    "happened to daisy, your pet rabbit.\n"
    "\n"
    "but now, you see spread before you more\n"
    "potential pain and gibbitude as a nation\n"
    "of demons run amok among our cities.\n"
    "\n"
    "next stop, hell on earth!"
)

C1TEXT = (
    "YOU HAVE ENTERED DEEPLY INTO THE INFESTED\n"
    "STARPORT. BUT SOMETHING IS WRONG. THE\n"
    "MONSTERS HAVE BROUGHT THEIR OWN REALITY\n"
    "WITH THEM, AND THE STARPORT'S TECHNOLOGY\n"
    "IS BEING SUBVERTED BY THEIR PRESENCE.\n"
    "\n"
    "AHEAD, YOU SEE AN OUTPOST OF HELL, A\n"
    "FORTIFIED ZONE. IF YOU CAN GET PAST IT,\n"
    "YOU CAN PENETRATE INTO THE HAUNTED HEART\n"
    "OF THE STARBASE AND FIND THE CONTROLLING\n"
    "SWITCH WHICH HOLDS EARTH'S POPULATION\n"
    "HOSTAGE."
)

C2TEXT = (
    "YOU HAVE WON! YOUR VICTORY HAS ENABLED\n"
    "HUMANKIND TO EVACUATE EARTH AND ESCAPE\n"
    "THE NIGHTMARE.  NOW YOU ARE THE ONLY\n"
    "HUMAN LEFT ON THE FACE OF THE PLANET.\n"
    "CANNIBAL MUTATIONS, CARNIVOROUS ALIENS,\n"
    "AND EVIL SPIRITS ARE YOUR ONLY NEIGHBORS.\n"
    "YOU SIT BACK AND WAIT FOR DEATH, CONTENT\n"
    "THAT YOU HAVE SAVED YOUR SPECIES.\n"
    "\n"
    "BUT THEN, EARTH CONTROL BEAMS DOWN A\n"
    "MESSAGE FROM SPACE: \"SENSORS HAVE LOCATED\n"
    "THE SOURCE OF THE ALIEN INVASION. IF YOU\n"
    "GO THERE, YOU MAY BE ABLE TO BLOCK THEIR\n"
    "ENTRY.  THE ALIEN BASE IS IN THE HEART OF\n"
    "YOUR OWN HOME CITY, NOT FAR FROM THE\n"
    "STARPORT.\" SLOWLY AND PAINFULLY YOU GET\n"
    "UP AND RETURN TO THE FRAY."
)

C3TEXT = (
    "YOU ARE AT THE CORRUPT HEART OF THE CITY,\n"
    "SURROUNDED BY THE CORPSES OF YOUR ENEMIES.\n"
    "YOU SEE NO WAY TO DESTROY THE CREATURES'\n"
    "ENTRYWAY ON THIS SIDE, SO YOU CLENCH YOUR\n"
    "TEETH AND PLUNGE THROUGH IT.\n"
    "\n"
    "THERE MUST BE A WAY TO CLOSE IT ON THE\n"
    "OTHER SIDE. WHAT DO YOU CARE IF YOU'VE\n"
    "GOT TO GO THROUGH HELL TO GET TO IT?"
)

C4TEXT = (
    "THE HORRENDOUS VISAGE OF THE BIGGEST\n"
    "DEMON YOU'VE EVER SEEN CRUMBLES BEFORE\n"
    "YOU, AFTER YOU PUMP YOUR ROCKETS INTO\n"
    "HIS EXPOSED BRAIN. THE MONSTER SHRIVELS\n"
    "UP AND DIES, ITS THRASHING LIMBS\n"
    "DEVASTATING UNTOLD MILES OF HELL'S\n"
    "SURFACE.\n"
    "\n"
    "YOU'VE DONE IT. THE INVASION IS OVER.\n"
    "EARTH IS SAVED. HELL IS A WRECK. YOU\n"
    "WONDER WHERE BAD FOLKS WILL GO WHEN THEY\n"
    "DIE, NOW. WIPING THE SWEAT FROM YOUR\n"
    "FOREHEAD YOU BEGIN THE LONG TREK BACK\n"
    "HOME. REBUILDING EARTH OUGHT TO BE A\n"
    "LOT MORE FUN THAN RUINING IT WAS.\n"
)

C5TEXT = (
    "CONGRATULATIONS, YOU'VE FOUND THE SECRET\n"
    "LEVEL! LOOKS LIKE IT'S BEEN BUILT BY\n"
    "HUMANS, RATHER THAN DEMONS. YOU WONDER\n"
    "WHO THE INMATES OF THIS CORNER OF HELL\n"
    "WILL BE."
)

C6TEXT = (
    "CONGRATULATIONS, YOU'VE FOUND THE\n"
    "SUPER SECRET LEVEL!  YOU'D BETTER\n"
    "BLAZE THROUGH THIS ONE!\n"
)

P1TEXT = (
    "You gloat over the steaming carcass of the\n"
    "Guardian.  With its death, you've wrested\n"
    "the Accelerator from the stinking claws\n"
    "of Hell.  You relax and glance around the\n"
    "room.  Damn!  There was supposed to be at\n"
    "least one working prototype, but you can't\n"
    "see it. The demons must have taken it.\n"
    "\n"
    "You must find the prototype, or all your\n"
    "struggles will have been wasted. Keep\n"
    "moving, keep fighting, keep killing.\n"
    "Oh yes, keep living, too."
)

P2TEXT = (
    "Even the deadly Arch-Vile labyrinth could\n"
    "not stop you, and you've gotten to the\n"
    "prototype Accelerator which is soon\n"
    "efficiently and permanently deactivated.\n"
    "\n"
    "You're good at that kind of thing."
)

P3TEXT = (
    "You've bashed and battered your way into\n"
    "the heart of the devil-hive.  Time for a\n"
    "Search-and-Destroy mission, aimed at the\n"
    "Gatekeeper, whose foul offspring is\n"
    "cascading to Earth.  Yeah, he's bad. But\n"
    "you know who's worse!\n"
    "\n"
    "Grinning evilly, you check your gear, and\n"
    "get ready to give the bastard a little Hell\n"
    "of your own making!"
)

P4TEXT = (
    "The Gatekeeper's evil face is splattered\n"
    "all over the place.  As its tattered corpse\n"
    "collapses, an inverted Gate forms and\n"
    "sucks down the shards of the last\n"
    "prototype Accelerator, not to mention the\n"
    "few remaining demons.  You're done. Hell\n"
    "has gone back to pounding bad dead folks \n"
    "instead of good live ones.  Remember to\n"
    "tell your grandkids to put a rocket\n"
    "launcher in your coffin. If you go to Hell\n"
    "when you die, you'll need it for some\n"
    "final cleaning-up ..."
)

P5TEXT = (
    "You've found the second-hardest level we\n"
    "got. Hope you have a saved game a level or\n"
    "two previous.  If not, be prepared to die\n"
    "aplenty. For master marines only."
)

P6TEXT = (
    "Betcha wondered just what WAS the hardest\n"
    "level we had ready for ya?  Now you know.\n"
    "No one gets out alive."
)

T1TEXT = (
    "You've fought your way out of the infested\n"
    "experimental labs.   It seems that UAC has\n"
    "once again gulped it down.  With their\n"
    "high turnover, it must be hard for poor\n"
    "old UAC to buy corporate health insurance\n"
    "nowadays..\n"
    "\n"
    "Ahead lies the military complex, now\n"
    "swarming with diseased horrors hot to get\n"
    "their teeth into you. With luck, the\n"
    "complex still has some warlike ordnance\n"
    "laying around."
)

T2TEXT = (
    "You hear the grinding of heavy machinery\n"
    "ahead.  You sure hope they're not stamping\n"
    "out new hellspawn, but you're ready to\n"
    "ream out a whole herd if you have to.\n"
    "They might be planning a blood feast, but\n"
    "you feel about as mean as two thousand\n"
    "maniacs packed into one mad killer.\n"
    "\n"
    "You don't plan to go down easy."
)

T3TEXT = (
    "The vista opening ahead looks real damn\n"
    "familiar. Smells familiar, too -- like\n"
    "fried excrement. You didn't like this\n"
    "place before, and you sure as hell ain't\n"
    "planning to like it now. The more you\n"
    "brood on it, the madder you get.\n"
    "Hefting your gun, an evil grin trickles\n"
    "onto your face. Time to take some names."
)

T4TEXT = (
    "Suddenly, all is silent, from one horizon\n"
    "to the other. The agonizing echo of Hell\n"
    "fades away, the nightmare sky turns to\n"
    "blue, the heaps of monster corpses start \n"
    "to evaporate along with the evil stench \n"
    "that filled the air. Jeeze, maybe you've\n"
    "done it. Have you really won?\n"
    "\n"
    "Something rumbles in the distance.\n"
    "A blue light begins to glow inside the\n"
    "ruined skull of the demon-spitter."
)

T5TEXT = (
    "What now? Looks totally different. Kind\n"
    "of like King Tut's condo. Well,\n"
    "whatever's here can't be any worse\n"
    "than usual. Can it?  Or maybe it's best\n"
    "to let sleeping gods lie.."
)

T6TEXT = (
    "Time for a vacation. You've burst the\n"
    "bowels of hell and by golly you're ready\n"
    "for a break. You mutter to yourself,\n"
    "Maybe someone else can kick Hell's ass\n"
    "next time around. Ahead lies a quiet town,\n"
    "with peaceful flowing water, quaint\n"
    "buildings, and presumably no Hellspawn.\n"
    "\n"
    "As you step off the transport, you hear\n"
    "the stomp of a cyberdemon's iron shoe."
)

CASTORDER = (
    ("ZOMBIEMAN", MT_POSSESSED),
    ("SHOTGUN GUY", MT_SHOTGUY),
    ("HEAVY WEAPON DUDE", MT_CHAINGUY),
    ("IMP", MT_TROOP),
    ("DEMON", MT_SERGEANT),
    ("LOST SOUL", MT_SKULL),
    ("CACODEMON", MT_HEAD),
    ("HELL KNIGHT", MT_KNIGHT),
    ("BARON OF HELL", MT_BRUISER),
    ("ARACHNOTRON", MT_BABY),
    ("PAIN ELEMENTAL", MT_PAIN),
    ("REVENANT", MT_UNDEAD),
    ("MANCUBUS", MT_FATSO),
    ("ARCH-VILE", MT_VILE),
    ("THE SPIDER MASTERMIND", MT_SPIDER),
    ("THE CYBERDEMON", MT_CYBORG),
    ("OUR HERO", MT_PLAYER),
)

_CAST_SFX = {
    S_PLAY_ATK1: "dshtgn",
    S_POSS_ATK2: "pistol",
    S_SPOS_ATK2: "shotgn",
    S_VILE_ATK2: "vilatk",
    S_SKEL_FIST2: "skeswg",
    S_SKEL_FIST4: "skepch",
    S_SKEL_MISS2: "skeatk",
    S_FATT_ATK8: "firsht",
    S_FATT_ATK5: "firsht",
    S_FATT_ATK2: "firsht",
    S_CPOS_ATK2: "shotgn",
    S_CPOS_ATK3: "shotgn",
    S_CPOS_ATK4: "shotgn",
    S_TROO_ATK3: "claw",
    S_SARG_ATK2: "sgtatk",
    S_BOSS_ATK2: "firsht",
    S_BOS2_ATK2: "firsht",
    S_HEAD_ATK2: "firsht",
    S_SKULL_ATK2: "sklatk",
    S_SPID_ATK2: "shotgn",
    S_SPID_ATK3: "shotgn",
    S_BSPI_ATK2: "plasma",
    S_CYBER_ATK2: "rlaunc",
    S_CYBER_ATK4: "rlaunc",
    S_CYBER_ATK6: "rlaunc",
    S_PAIN_ATK3: "sklatk",
}

_D2_SCREENS = {
    6: ("SLIME16", C1TEXT),
    11: ("RROCK14", C2TEXT),
    20: ("RROCK07", C3TEXT),
    30: ("RROCK17", C4TEXT),
    15: ("RROCK13", C5TEXT),
    31: ("RROCK19", C6TEXT),
}
_TNT_SCREENS = {
    6: ("SLIME16", T1TEXT),
    11: ("RROCK14", T2TEXT),
    20: ("RROCK07", T3TEXT),
    30: ("RROCK17", T4TEXT),
    15: ("RROCK13", T5TEXT),
    31: ("RROCK19", T6TEXT),
}
_PLUT_SCREENS = {
    6: ("SLIME16", P1TEXT),
    11: ("RROCK14", P2TEXT),
    20: ("RROCK07", P3TEXT),
    30: ("RROCK17", P4TEXT),
    15: ("RROCK13", P5TEXT),
    31: ("RROCK19", P6TEXT),
}


def commercial_finale_map(mapn: int, secret: bool) -> bool:
    if mapn in (6, 11, 20, 30):
        return True
    return secret and mapn in (15, 31)


def _mission_screens(iwad_path: str) -> dict[int, tuple[str, str]]:
    name = os.path.basename(iwad_path or "").lower()
    if "tnt" in name:
        return _TNT_SCREENS
    if "plut" in name:
        return _PLUT_SCREENS
    return _D2_SCREENS


class Finale:
    def __init__(self, game) -> None:
        self.game = game
        self.stage = STAGE_TEXT
        self.count = 0
        self.done = False
        self.action = ""
        commercial = game.wad.check_num_for_name("MAP01") >= 0
        self.commercial = commercial
        if commercial:
            screens = _mission_screens(getattr(game, "iwad_path", ""))
            flat, text = screens.get(game.mapn, ("SLIME16", C1TEXT))
            self.text = text
            self.flat = flat
            game.sound.change_music("read_m", looping=True)
        else:
            texts = {1: E1TEXT, 2: E2TEXT, 3: E3TEXT, 4: E4TEXT}
            flats = {1: "FLOOR4_8", 2: "SFLR6_1", 3: "MFLR8_4", 4: "MFLR8_3"}
            self.text = texts.get(game.episode, E1TEXT)
            self.flat = flats.get(game.episode, "FLOOR4_8")
            game.sound.change_music("victor", looping=True)
        self._flat_lump = None
        n = game.wad.check_num_for_name(self.flat)
        if n >= 0:
            self._flat_lump = game.wad.cache_lump_num(n)
        self._art = None
        self._pfub1 = None
        self._pfub2 = None
        self._bossback = None
        self._last_bunny_stage = -1
        self.castnum = 0
        self.caststate = S_NULL
        self.casttics = 0
        self.castdeath = False
        self.castframes = 0
        self.castonmelee = 0
        self.castattacking = False
        if commercial:
            art = "CREDIT" if game.wad.check_num_for_name("CREDIT") >= 0 else "HELP2"
        elif game.episode == 2:
            art = "VICTORY2"
        elif game.episode == 4:
            art = "ENDPIC"
        else:
            art = "CREDIT" if game.wad.check_num_for_name("CREDIT") >= 0 else "HELP2"
        n = game.wad.check_num_for_name(art)
        if n < 0:
            n = game.wad.check_num_for_name("HELP1")
        if n >= 0:
            self._art = game.wad.cache_lump_num(n)
        if game.episode == 3 and not commercial:
            n1 = game.wad.check_num_for_name("PFUB1")
            n2 = game.wad.check_num_for_name("PFUB2")
            if n1 >= 0:
                self._pfub1 = game.wad.cache_lump_num(n1)
            if n2 >= 0:
                self._pfub2 = game.wad.cache_lump_num(n2)
        n = game.wad.check_num_for_name("BOSSBACK")
        if n >= 0:
            self._bossback = game.wad.cache_lump_num(n)

    def ticker(self) -> None:
        if self.commercial and self.stage == STAGE_TEXT and self.count > 50 and self._want_skip():
            if self.game.mapn == 30:
                self._start_cast()
            else:
                self.action = "worlddone"
                self.done = True
                return
        self.count += 1
        if self.stage == STAGE_CAST:
            self._cast_ticker()
            return
        if self.commercial:
            return
        if self.stage == STAGE_TEXT:
            if self.count > len(self.text) * TEXTSPEED + TEXTWAIT:
                self.stage = STAGE_ART
                self.count = 0
                self.game.force_wipe = True
                if self.game.episode == 3:
                    self.game.sound.change_music("bunny", looping=True)
        elif self.stage == STAGE_ART:
            skip_after = 1130 if self._pfub1 and self._pfub2 else 10
            if self._want_skip() and self.count > skip_after:
                self.done = True
                self.action = "title"

    def responder(self) -> bool:
        if self.stage != STAGE_CAST or self.castdeath:
            return False
        if not self._want_skip():
            return False
        info = MOBJINFO[CASTORDER[self.castnum][1]]
        self.castdeath = True
        self.caststate = info[MI_DEATHSTATE]
        self.casttics = STATES[self.caststate][2]
        if self.casttics == -1:
            self.casttics = 15
        self.castframes = 0
        self.castattacking = False
        return True

    def _start_cast(self) -> None:
        self.game.force_wipe = True
        self.castnum = 0
        info = MOBJINFO[CASTORDER[0][1]]
        self.caststate = info[MI_SEESTATE]
        self.casttics = STATES[self.caststate][2]
        self.castdeath = False
        self.stage = STAGE_CAST
        self.castframes = 0
        self.castonmelee = 0
        self.castattacking = False
        self.game.sound.change_music("evil", looping=True)

    def _cast_info(self):
        return MOBJINFO[CASTORDER[self.castnum][1]]

    def _stop_attack(self) -> None:
        self.castattacking = False
        self.castframes = 0
        self.caststate = self._cast_info()[MI_SEESTATE]

    def _cast_ticker(self) -> None:
        self.casttics -= 1
        if self.casttics > 0:
            return
        st = STATES[self.caststate]
        if st[2] == -1 or st[4] == S_NULL:
            self.castnum += 1
            self.castdeath = False
            if self.castnum >= len(CASTORDER):
                self.castnum = 0
            self.caststate = self._cast_info()[MI_SEESTATE]
            self.castframes = 0
        else:
            if self.caststate == S_PLAY_ATK1:
                self._stop_attack()
            else:
                nxt = st[4]
                self.caststate = nxt
                self.castframes += 1
                sfx = _CAST_SFX.get(nxt)
                if sfx:
                    self.game.sound.play(sfx)
        if self.castframes == 12:
            self.castattacking = True
            info = self._cast_info()
            self.caststate = info[MI_MELEESTATE] if self.castonmelee else info[MI_MISSILESTATE]
            self.castonmelee ^= 1
            if self.caststate == S_NULL:
                self.caststate = info[MI_MELEESTATE] if self.castonmelee else info[MI_MISSILESTATE]
        if self.castattacking:
            if self.castframes == 24 or self.caststate == self._cast_info()[MI_SEESTATE]:
                self._stop_attack()
        self.casttics = STATES[self.caststate][2]
        if self.casttics == -1:
            self.casttics = 15

    def _want_skip(self) -> bool:
        if self.game.menu and self.game.menu.active:
            return False
        if getattr(self.game, "mouse_fire", False):
            return True
        k = self.game.keys
        return bool(
            pygame.K_LCTRL in k
            or pygame.K_RCTRL in k
            or pygame.K_SPACE in k
            or pygame.K_RETURN in k
            or pygame.K_KP_ENTER in k
            or pygame.K_e in k
        )

    def draw(self, fb: bytearray) -> None:
        if self.stage == STAGE_CAST:
            self._draw_cast(fb)
            return
        if self.stage == STAGE_ART:
            if self.game.episode == 3 and self._pfub1 and self._pfub2:
                self._draw_bunny(fb)
            elif self._art:
                fill(fb, 0)
                draw_patch(fb, 0, 0, self._art)
            return
        self._draw_text(fb)

    def _draw_cast(self, fb: bytearray) -> None:
        fill(fb, 0)
        if self._bossback:
            draw_patch(fb, 0, 0, self._bossback)
        self._cast_print(fb, CASTORDER[self.castnum][0])
        st = STATES[self.caststate]
        spr = SPRNAMES[st[0]] if 0 <= st[0] < len(SPRNAMES) else ""
        found = lookup_sprite(self.game.res, spr, 0, 0, st[1] & FF_FRAMEMASK) if self.game.res else None
        if not found:
            return
        lump, flip = found
        patch = self.game.wad.cache_lump_num(lump)
        draw_patch(fb, 160, 170, patch, flipped=bool(flip))

    def _cast_print(self, fb: bytearray, text: str) -> None:
        width = 0
        for ch in text:
            code = ord(ch.upper())
            if ch == " " or code < HU_FONTSTART or code > HU_FONTEND:
                width += 4
                continue
            p = self._font(code)
            if not p:
                width += 4
                continue
            w, _h, _l, _t = patch_size(p)
            width += w
        cx = 160 - width // 2
        for ch in text:
            code = ord(ch.upper())
            if ch == " " or code < HU_FONTSTART or code > HU_FONTEND:
                cx += 4
                continue
            p = self._font(code)
            if not p:
                cx += 4
                continue
            w, _h, _l, _t = patch_size(p)
            draw_patch(fb, cx, 180, p)
            cx += w

    def _draw_bunny(self, fb: bytearray) -> None:
        fill(fb, 0)
        scroll = max(0, min(320, 320 - (self.count - 230) // 2))
        for x in range(SCREENWIDTH):
            column = x + scroll
            patch = self._pfub2 if column < 320 else self._pfub1
            self._draw_patch_column(fb, x, patch, column if column < 320 else column - 320)
        if self.count < 1130:
            return
        stage = 0 if self.count < 1180 else min(6, (self.count - 1180) // 5)
        if stage > self._last_bunny_stage:
            self.game.sound.play("pistol")
            self._last_bunny_stage = stage
        n = self.game.wad.check_num_for_name(f"END{stage}")
        if n >= 0:
            draw_patch(fb, (320 - 104) // 2, (200 - 64) // 2, self.game.wad.cache_lump_num(n))

    def _draw_patch_column(self, fb: bytearray, x: int, patch: bytes, column: int) -> None:
        if column < 0:
            return
        offset_pos = 8 + column * 4
        if offset_pos + 4 > len(patch):
            return
        offset = _u32(patch, offset_pos)
        while offset < len(patch) and patch[offset] != 255:
            top = patch[offset]
            length = patch[offset + 1]
            source = offset + 3
            for i in range(length):
                if top + i >= SCREENHEIGHT:
                    break
                fb[(top + i) * SCREENWIDTH + x] = patch[source + i]
            offset += length + 4

    def _fill_flat(self, fb: bytearray) -> None:
        lump = self._flat_lump
        if not lump or len(lump) < 4096:
            fill(fb, 0)
            return
        for y in range(200):
            row = (y & 63) << 6
            dest = y * SCREENWIDTH
            for x in range(0, SCREENWIDTH, 64):
                n = min(64, SCREENWIDTH - x)
                fb[dest + x : dest + x + n] = lump[row : row + n]

    def _draw_text(self, fb: bytearray) -> None:
        self._fill_flat(fb)
        nshow = self.count // TEXTSPEED
        cx, cy = 10, 10
        for i, ch in enumerate(self.text):
            if i >= nshow:
                break
            if ch == "\n":
                cx = 10
                cy += 11
                continue
            code = ord(ch.upper())
            if ch == " " or code < HU_FONTSTART or code > HU_FONTEND:
                cx += 4
                continue
            p = self._font(code)
            if not p:
                cx += 4
                continue
            w, _h, _l, _t = patch_size(p)
            if cx + w > SCREENWIDTH:
                break
            draw_patch(fb, cx, cy, p)
            cx += w

    def _font(self, code: int):
        if code - HU_FONTSTART < 0 or code - HU_FONTSTART >= HU_FONTSIZE:
            return None
        n = self.game.wad.check_num_for_name(f"STCFN{code:03d}")
        if n < 0:
            return None
        return self.game.wad.cache_lump_num(n)
