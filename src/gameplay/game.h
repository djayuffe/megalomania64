#ifndef MLM_NATIVE_GAME_H
#define MLM_NATIVE_GAME_H
#include "world.h"
#define NG_STATE_BYTES 128
/* Persisted bytes have a fixed wire layout, independent of host C alignment. */
#define NG_ISLAND 12
#define NG_HUMAN 13
#define NG_ACTIVE 14
#define NG_STATUS 15
#define NG_SPEED 16
#define NG_PAUSED 17
#define NG_SELECTED 18
#define NG_CATEGORY 19
#define NG_DESIGN 20
#define NG_DEPOSIT 21
#define NG_BUILDING 22
#define NG_HOTSEAT 23
#define NG_DIFFICULTY 24
#define NG_TURRET 25
#define NG_SEED 26
#define NG_CLOCK 28
#define NG_ALLIES 30
#define NG_DONE 34
#define NG_WITHDRAW 38
#define NG_POOL 116
#define NG_DEPLOY 118
#define NG_PHASE 126
#define NG_START 127
#define NG_TRUCE 84
#define NG_RESERVE 42
#define NG_AI 50
#define NG_ORIGIN 82
#define NG_NUKE 83
#define NG_PLAYING 0
#define NG_WON 1
#define NG_LOST 2
#define NG_COMPLETE 3
extern uint8_t ng_state[NG_STATE_BYTES],ng_terrain[16],ng_owners[16],ng_ages[16],ng_ruined[16],ng_event;
extern uint16_t ng_people[16],ng_units[16][4],ng_strength[16][4],ng_presence[4];
void ng_new(void);
void ng_reset_pacts(void);
void ng_prepare_island(void);
uint8_t ng_campaign_action(uint8_t key);
void ng_rule(uint8_t op,uint16_t a,uint16_t b,uint16_t c);
void ng_cache(void);
void ng_step(uint16_t elapsed);
void ng_clock(uint16_t elapsed);
void ng_outcome(void);
uint8_t ng_move(uint8_t from,uint8_t to,uint8_t faction);
uint8_t ng_arm(uint8_t age);
uint8_t ng_repair(uint8_t age,uint8_t building);
uint8_t ng_defend(uint8_t age,uint8_t building,uint8_t slot);
uint8_t ng_launch(uint8_t from,uint8_t to,uint8_t faction,uint8_t retaliate);
void ng_negotiate(uint8_t other);
void ng_break(uint8_t other);
void ng_shutdown(void);
#endif
