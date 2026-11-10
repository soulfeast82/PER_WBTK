# WBTK talk notes (Socratic, not scoped)

Ideas Jermaine reached in Socratic talks about WBTK. Nothing here is specced or built. Whether and when is his call.

## 2026-10-11, part 1: grow everything out of Build Mode

- **Build Mode is the genesis.** Everything else in WBTK should grow out of it, not sit in its own sidebar panel. His pain today is the UI: button fatigue and redundancy.
- **Click the thing to add to it.** A pipe comes from the building itself: click the wall and add it.
- **The surface decides the menu.** A wall offers pipes, vents, cables and signs, never trees or fences. He called it "almost tileable", and it should feel "smart, frictionless, and clean".
- **Draw the path, with smart guides.** He decides where a pipe goes by drawing it. It snaps to the wall and follows it, goes around windows and bends at corners. The guides snap to window edges and wall corners, using the mesh's own edges.

## 2026-10-19, part 2: walkways and "tileable"

- **Walkways stay separate** from Build Mode: a pipe grows out of one thing, a walkway grows between two (building to building, across a gap between land masses, a sidewalk). Each end needs a structure or surface.
- **Making one:** pick the walkway type first, then stretch a line (a curve) like a measuring tape between the two ends. Dots are the points; drag a dot to shape it, then apply.
- **What "tileable" means to him:** a 3DCoat TikTok he saved (Downloads/Download.mp4, @3dcoat, 60 s). Pipe pieces, valves, joints and vents snap end to end through their own joints ("instead of a traditional pivot"), new elements fill in between, and a whole machine wall builds up from pieces that connect. Like Animal Crossing's easy alignment, raised for game development.

## 2026-10-25, part 3: his mockup

His sketch: `talk_refs/walkway_pipe_mockup_2026-10-25.webp`.

1. **Choose the walkway path type** first (a tile swatch, e.g. a grating).
2. **Click, drag and click** to connect edge to edge of the meshes. Dots mark the points, and the path can turn at right angles. Then confirm and apply. The same gesture works for pipes and other types on walls.
3. **Confirmed and applied:** the grating walkway fills the path and turns its corner with a corner piece; on the wall, the pipe follows the dots and bends with rounded elbows.

## 2026-11-01, part 4: end pieces, and two add-ons he bought for research

- **Path ends:** a plain walkway end may match the middle, but railings need end caps. So WBTK reads three spots on a path so far: straight, corner, end.
- **Research add-ons** (zips in his Downloads; read for ideas, not for copying code):
  - **QuickSnap 1.5.1** (Superhive, Blender 5.0+): Maya/3ds Max-style vertex snap. Grab a point on an object and drop it on a vertex, edge midpoint, face centre or origin of another. Works as click-drag or as two clicks, with no selection needed; hotkeys 1/2/3/O switch the snap target and an icon by the mouse shows which one.
  - **Level Builder 1.0** (Blender 2.80 era): pick an asset from a preview library and place it on whatever surface is under the mouse (ray cast), with randomness options and a rigid-body helper that drops objects with physics, then bakes them back.
- **His pick: QuickSnap**, "because it lines things up without me fiddling". The ease he means is alignment that happens for him.
- **Who chooses what (2026-11-02):** a QuickSnap snap is two choices, the grab point and the drop spot. His split: **he picks the drop spot, WBTK picks the grab point.**
- **How WBTK knows the grab point:** each piece carries its own joints (as in the 3DCoat clip), and the person who made the kit puts them there.
- **His own pieces** would possibly get their joints through WBTK. Open: what happens to a bought kit piece (e.g. Citypunk) that arrives with no joints.
- **Joints can be read from the shape:** he finds a railing's joints by eye at "the open ends where it would connect". So WBTK could guess joints from open ends instead of anyone marking them by hand.
- **Fixing a wrong guess:** show the joints as dots he can click to remove (e.g. a valve handle's flat tip read as a third joint). Same dot language as his walkway path points.
- **When dots show:** only when he hovers or grabs a piece. A full street corner would otherwise be buried in dots.

## 2026-11-02, part 5: the drop side

- **Holding a pipe over a wall**, he wants to see only the wall's edges and the window corners, not every brick's corners and midpoints.
- **The piece in hand decides the drop spots.** A shop sign on the same wall wants different spots than a pipe. Mirror of part 1's rule (the surface decides the menu): the surface decides what you can add, and what you're holding decides where it can go.
- **A sign's spots:** above the door, centred between the windows.
- **Two kinds of drop spot.** A pipe's spots are real mesh points (edges, corners). "Centred between the windows" sits on a blank face with no point there: it is *made* from two real ones, the way he'd find it with a tape: measure from the two window edges, cut it in half. QuickSnap only snaps to real points; WBTK would also need made spots.
- **Proof it found a made spot:** a guide line from both windows lights up when the sign clicks into the centre. These are the "smart guides" he asked for in part 1, now with a reason: they show the spots the mesh doesn't have.

## 2026-11-02, part 6: non-generic windows and doors

- **Generic windows** sit in the background and don't pull the eye. They come in rows, all the same size, evenly spaced.
- **Variety comes from type:** wide windows that wrap around the corner, store windows. "I guess it's the type as well."
- **What's inside decides the window.** Store windows sit on the ground floor because the shops are there, for people walking by. The window follows the room behind it.
- **Test: a stairwell.** Its windows are staggered between the floors, out of line with the apartment rows. A window that breaks the grid has a reason, and that reason is what makes it non-generic.
- **Tell WBTK what the room is, not how many windows.** Today Build Mode auto-fits an even row of windows to a WINDOW wall (the generic picture). His idea: tag a wall or floor with its room (shop, stairwell, …) and let the windows follow from it.

## 2026-11-02, part 7: CHARTA + WBTK, "the wizard in the world"

- **Every WBTK move he pictured today** (pipe on a wall, sign between windows, stairwell from the street) **was on the street, looking at the wall.** CHARTA today feels like looking down at a map (see the CHARTA wizard gap, 10-05).
- **What only the view from above gives:** seeing the whole district layout at once. So each view is good at something: above = the layout, street = the walls and details.
- **The wizard's move:** from the street, zoom out and the camera rises above the district. One continuous camera, no jump between views.
- **Today's version:** save, open the browser, find CHARTA, look for the district. Four steps across two apps, where the wizard has one zoom.
- **And the two don't know each other:** CHARTA's map shows only the blocks placed in CHARTA, not the building just made in Blender. Two separate copies of the district. (On 10-05 he floated CHARTA → WBTK auto-blockout, one way only.)
- **One world (2026-11-04):** a CHARTA block and a WBTK building are the same object seen from two heights, and changes flow both ways. This replaces the one-way idea from 10-05.
- **Editing from above (2026-11-06):** after an hour of street-level work, pushing or shrinking the block from above should carry the pipes, sign and windows along. They "move with and scale appropriately with each surface". He rates shrinking as the harder case, and his idea for it: a tiled run like a pipe could drop pieces as the wall gets smaller (or add them as it grows).
- **What gives way when a block shrinks:** the door stays real size and the blank wall gives up the space. "Scale appropriately" means details keep their size and the empty wall absorbs the change.
- **When the wall runs out:** if shrinking leaves room for only one window, WBTK stops and shows him, and he picks what goes. It never decides that on its own (e.g. the second window, or a sign whose "between the windows" no longer exists).
- **Blender's job, in his words so far:** "more than the block out but the details of the world". His answer to whether the inside-the-world feeling is there yet: he's still working it out, and he pointed at where the details get made. WBTK's CLAUDE.md design laws say blocking and layout happen in UE5.
- **Where the wizard stands to judge: Unreal**, "because that's what the player actually sees. It is where the world comes together." So far: CHARTA = layout from above, Blender = making the details, Unreal = judging the result.
- **Fix it where you see it:** a sign too high or a pipe crossing a window gets fixed right there in Unreal, without leaving. Having to leave would make his "virgo adhd" rage.
- **Fixes survive:** a sign lowered in Unreal stays where he put it, even after the building is changed in Blender and sent over again.
- **One notebook, kept in Unreal,** "since that's where the world comes together". One record of where things are, not two that sync.
- **Where things go happens in Unreal, and Blender just makes the pieces.** So the placing moves from this talk (pipe along a wall, made spots, guide lines, the stop-and-pick) would live in Unreal, not in Blender. This is a talk conclusion, not a ruling. It would move much of what WBTK does today out of Blender, and it pulls against part 1 ("Build Mode is the genesis"). Open: what happens to Build Mode.
- **A building is put together in Unreal from smaller pieces** (his leaning, with a question mark): modular pieces that make large buildings of various sizes.
- **Build Mode's new job: it makes the kit pieces.** It stays the genesis, of the pieces instead of whole buildings. Not a ruling.
- **Not yet talked through:** WBTK's Strategic Pivot (locked 2026-07-06, CLAUDE.md) makes Buildify in Blender the building engine and has Build Mode footprints feed it. This talk's split would need that re-examined. Landmarks as one-off whole buildings also weren't discussed.
- **His memory of the Buildify intent (2026-11-06):** "I honestly didn't want to really integrate buildify into WBTK. I wanted WBTK Build Mode to take aspects from it and keep things native. But maybe I was confused." Not a ruling yet. CLAUDE.md's Evolution Clause (long-term fork into WBTK's own library, only when forced) is the closest thing on record. Open: which aspects he wanted.
- **Buildify's role under the new split:** "not sure if it has as strong a role anymore if everything modular [is] built in Unreal." Doubt, not a ruling.
- **The feel he wants when building in Unreal:** "I'm putting [the] world together, that I can snap and tile together."
- **A wall from the walkway gesture:** pick a wall type, "stretch along the wall for one floor, then drag up for six". Two strokes, ~48 pieces placed; WBTK fills the straights, corners and ends the way it fills a walkway path. This is the same shape of move Buildify makes in Blender (footprint in, floors stack up), now pictured in Unreal. Open: where the shop front and the staggered stairwell (part 6) enter, since a drag-up makes six identical floors.
- **When the ground floor becomes a shop row:** during the drag up, "when the number goes past 1". The moment a second floor exists, the stack splits into ground and the rest; the ground floor is where the shops (part 6) go. One floor alone has nothing to split.
- **The stairwell is pointed at afterward:** "this strip is the stairwell", and the windows in that strip re-sort to staggered. So two kinds of room tag: the shop row comes free from the drag (ground floor, once floors > 1); the stairwell is a strip he names on the standing wall. Same "tell WBTK what the room is" rule from part 6, two entry points.
- **Who owns the three moves (stretch, drag up, point at a strip): "still WBTK, living inside Unreal."** His picture now: WBTK has two homes. In Blender, Build Mode makes the kit pieces. In Unreal, WBTK puts them together (the three moves, the pipe/sign drop spots, the stop-and-pick, the one notebook). Not a ruling. This would be a UE plugin or editor tool that does not exist today; WBTK's CLAUDE.md design law "blocking/layout happens in UE5; WBTK output = architecture assets" already points this way. Buildify's job (stack floors from a footprint) is what the drag-up does here, which is why he doubts its role.
- **The walkway gesture moves to Unreal too:** "the walkway connects two buildings that are already placed." His rule for which home a move belongs to: if it needs things that are already standing in the world (two buildings, a wall), it happens in Unreal. Blender only ever holds one piece at a time.
- **Joints are stamped in Blender:** "Build Mode stamps them when it makes the piece." So the joint is part of the piece and travels with it; WBTK-in-Unreal reads what came, and open-end guessing (part 4) is the fallback for bought kits that arrive without joints. In UE terms the joint would be a socket on the static mesh; Blender already exports empties named SOCKET_* as UE sockets through FBX, so the stamp has a known road.
- **Build Mode tomorrow, in his words:** first click = the wall type (WINDOW, DOOR, SOLID...); generate = "one slab, the piece the drag-up repeats" (about one bay wide, one storey tall, joints stamped). Not a whole building cut into pieces. So Build Mode's blocks, stacking and per-wall types fold into a piece maker: wall type becomes the piece's identity, not a setting on one face of a building.
- **Landmarks:** "a landmark gets built in Blender as one whole piece." So the Blender home makes two things: repeatable kit slabs (Build Mode) and one-off whole landmarks (modelled, not generated). Both arrive in Unreal as pieces with joints, so a walkway can still connect to a landmark and a pipe can still run along its wall. Open: whether a landmark gets its joints stamped by Build Mode or by hand.
- **Landmark joints:** "Blender would stamp them together", so the same joint stamp covers slabs and landmarks, in Blender, before export.
- **Region DNA:** "should definitely swap kits." Region DNA stays, and its job in the two-homes picture is the kit switcher: pick a district, the drag-up tiles that district's slabs. (The July pivot already had Region DNA switching Buildify kits; the job survives, the engine under it changes.)
- **"Can WBTK start being built to this version?" (2026-11-06):** asked at the end of the talk. Answer given: not the whole tool yet; see the reply in the chat and the line in `_gamedocs/NOW.md`. The first build, if he wants one, is a small proof of the bridge: one slab out of Build Mode with joints stamped, exported, two of them snapped together in Unreal. The Buildify ruling comes before any larger build.
- **RULED 2026-11-06: "Replace the pivot with the two homes."** The July Buildify Strategic Pivot is superseded (banner added to `CLAUDE.md`, ruling in `_gamedocs/NOW.md`). Everything in part 7 is now the direction WBTK is specced against. Still only a direction: no build asked for.

## 2026-11-06, part 8: CHARTA's zoom, after the two homes

- **Where the zoom-out lands:** scroll out from the shop front in Unreal, the camera climbs, and at the top you see "CHARTA's blocks drawn inside Unreal." Not the browser. So the district view is a view inside Unreal, drawn from the same world file CHARTA edits today.
- **Pushing a block:** "push it right there in Unreal from above." So the move CHARTA exists for (grab a block, push it till it feels right) also happens in Unreal. Both heights of the one object are edited in the same place. Open: what the browser CHARTA is still for.
- **What the browser CHARTA is still for (2026-11-07):** he reaches for the console side first: "CHARTA is part of the console system", so it stays where the canon, the Ledger, the party timeline and the Council live; and "iPad would work", the couch view with no engine open. Not a strong pull. The honest reading: in the two-homes world CHARTA's layout job moves to Unreal, and what keeps the browser one alive is its tie to the rest of the console and the iPad, not its map.
- **A push from the iPad reaches Unreal:** "the building moves at the desk." So the browser CHARTA stays an editor, not a window, and the one notebook (part 7: kept in Unreal) has to take writes from two doors: Unreal from above or the street, and CHARTA from the couch. The 10-05 sync ruling (desktop is home, Pages console is a viewer) pulls the other way for the Pages copy; the desktop console already has a Remote Control Python bridge to UE (ue_ping.py, 09-26), so the road exists for the desk. The iPad road does not exist today.
- **The couch push waits as "a letter on the doormat Unreal reads when it opens."** The notebook stays in Unreal; CHARTA never holds the truth, it writes a letter. In plain terms: CHARTA saves its push to the world file in `_gamedocs` (the Ctrl+S route already exists, Lane D2), and WBTK-in-Unreal reads that file on open and applies what changed. Unreal's notebook stays the one truth; the world file is the doormat. Open: what happens when the letter and the notebook disagree (he moved the same block at the desk after the couch push).
- **When the letter and the notebook disagree:** "stop and show me, let me pick which push wins." Same rule as the wall running out (part 7): WBTK never settles a conflict on its own. Unreal shows both positions on open, he picks. This is the third time he chose stop-and-pick over an automatic rule; it is a WBTK law now in all but name.
- **The CHARTA gap (10-05) is closed by this picture, in his words: "it closes the gap, that's the wizard."** The wizard = standing on the street in Unreal, one scroll up to the district blocks, push, one scroll back down; CHARTA in the browser is the couch door that writes letters. Talk conclusion, not a build; the Unreal half does not exist yet.

## 2026-11-08, part 9: corner and roof pieces

(The drag-up of part 7 covers the straight bays. This part is about where a wall turns and where it stops going up.)
