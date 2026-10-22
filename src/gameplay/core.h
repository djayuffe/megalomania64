#ifndef MLM_GAMEPLAY_CORE_H
#define MLM_GAMEPLAY_CORE_H
#include <stdint.h>
/* Original DOS record layout retained for differential verification. Runtime
 * compaction and the new game UI are separate from these rule translations. */
#define GP_SECTOR_BYTES 0x449
#define GP_REQ_BYTES 32
#define GP_POP 0x404
#define GP_FREE 0x406
#define GP_BIRTH_DEADLINE 0xb4
#define GP_BIRTH_PROGRESS 0xb8
#define GP_BIRTH_RATE 0xbc
#define GP_DEPOSITS 0x134
#define GP_STOCKS 0x174
#define GP_INVENTORY 0xe6
extern uint8_t gp_sector[GP_SECTOR_BYTES];
extern uint8_t gp_request[GP_REQ_BYTES];
extern uint8_t gp_recipe[10];
extern uint8_t gp_personality[56],gp_plan[28];
void gp_economy_plan(void);
void gp_economy_allocate(void);
void gp_economy_scan(void);
void gp_defence_plan(void);
void gp_repair_plan(void);
uint16_t gp_sos(void);
uint16_t gp_reinforce(void);
uint16_t gp_max_army(uint16_t first,uint16_t last);
uint16_t gp_retreat(uint16_t faction);
uint16_t gp_hostile(uint16_t faction);
void gp_travel_losses(uint16_t faction);
uint16_t gp_make_army(uint16_t strength,uint16_t people,uint16_t minimum_age,uint16_t fallback);
extern uint8_t gp_routes[16]; /* 0 sea, 1 traversable, 3 terminal, 4 reached */
extern uint8_t gp_classes[20];
/* Four building types: ten age-specific health words, turret count word,
 * turret-record offset word (24 bytes each). Loaded from audited rule data. */
extern uint8_t gp_buildings[96];
extern uint8_t gp_patterns[270]; /* 30 templates: count, four group/cost pairs */
extern uint8_t gp_groups[20]; /* inclusive first/last element in ten groups */
extern uint8_t gp_complexity[14];
extern uint8_t gp_manufacture[14];
extern uint8_t gp_research_points[12];
extern uint8_t gp_technology_points[20];
extern uint8_t gp_army[11]; /* incoming units, mutated to unaccepted remainder */
extern uint8_t gp_army_rules[66]; /* 11 health, strength and crew-count words */
extern uint8_t gp_defence_rules[60]; /* ten health, strength, crew-count words */
extern uint8_t gp_alliances[4]; /* faction bitsets, including the faction itself */
extern uint8_t gp_repair_caps[80]; /* original double-indexed shield health caps */
extern uint8_t gp_shield_rules[20]; /* repair points for ten shield ages */
extern uint8_t gp_owned[4],gp_retired[4],gp_army_sectors[4]; /* derived whole-world counts */
extern uint8_t gp_combat_rules[10]; /* army %, turret %, tick divisor: five words */
/* request: opcode byte0, elapsed/argument word2, slot/kind word4, age word6,
 * count word8, seed word10; result word12; task base word14, scale word16. */
void gp_dispatch(void);
#endif
