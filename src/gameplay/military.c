/* DOS 16B4:22A3. Native army assembly, including rollback and nuclear fallback.
 * Stack locals keep the leaf overlay within the shared 6502 RAM budget. */
#include "core.h"
#ifdef __CC65__
#pragma code-name ("MILITARY")
#endif
static uint16_t r(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void w(uint8_t *p,uint16_t n) {p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static uint16_t take(uint16_t n,uint16_t age) {
    gp_request[0]=46;w(gp_request+2,n);w(gp_request+4,2);w(gp_request+6,age);gp_dispatch();return r(gp_request+12);
}
static void refund(uint16_t age,uint16_t n) {
    uint16_t at,i,e,stock;
    if(age<4 && (r(gp_sector+0x126)&((uint16_t)1<<age))) {
        at=0x264+age*10;
        for(i=0;i<10;i+=2) {e=gp_sector[at+i];if(e<20) {
            stock=GP_STOCKS+e*2;w(gp_sector+stock,r(gp_sector+stock)+(uint16_t)(gp_sector[at+i+1]*n));
        }}
    }else {at=0x10e + age*2;stock=r(gp_sector+at)+n;w(gp_sector+at,stock>200?200:stock);}
}
uint16_t gp_make_army(uint16_t strength,uint16_t minimum_people,uint16_t minimum_age,uint16_t fallback) {
    uint16_t free,crews,units,n,power,crew,i;int16_t age;uint8_t unarmed;
    free=r(gp_sector+GP_FREE);crews=0;units=0;unarmed=minimum_age==10;if(unarmed)minimum_age=0;
    for(i=0;i<11;++i)gp_army[i]=0;
    if(fallback==8 && !r(gp_sector+0x120) && r(gp_sector+0x11e))goto nuclear;
    if(minimum_people>free)goto nuclear;
    age=9;
    for(;;) {
        if((int16_t)strength<=0)break;
        if(age!=8) {
            power=r(gp_army_rules+22+(uint16_t)age*2);if(!power)goto failed;
            n=(uint16_t)(strength+power-1)/power;if((uint16_t)(units+n)>250)goto failed;
            n=take(n,(uint16_t)age);
            if(n) {
                gp_army[age]+=(uint8_t)n;units+=n;crew=r(gp_army_rules+44+(uint16_t)age*2);crews+=(uint16_t)(n*crew);
                if(crews>free)goto failed;
                strength-=(uint16_t)(n*power);if((int16_t)strength<=0)break;
            }
        }
        --age;if(age<(int16_t)minimum_age) {
            if(!unarmed)goto failed;
            power=r(gp_army_rules+42);if(!power)goto failed;
            n=(uint16_t)(strength+power-1)/power;units+=n;crews+=n;
            if(units>250 || crews>free)goto failed;gp_army[10]+=(uint8_t)n;break;
        }
    }
    if(crews>=minimum_people)goto complete;
    while(age>=(int16_t)minimum_age) {
        if(age!=8) {
            crew=r(gp_army_rules+44+(uint16_t)age*2);if(!crew)goto failed;
            n=(uint16_t)(minimum_people-crews+crew-1)/crew;
            if((uint16_t)(units+n)>250)goto complete;
            n=take(n,(uint16_t)age);
            if(n) {gp_army[age]+=(uint8_t)n;units+=n;crews+=(uint16_t)(n*crew);if(crews>free)goto failed;if(crews>=minimum_people)goto complete;}
        }
        --age;
    }
    if(!unarmed)goto failed;
    n=minimum_people-crews;units+=n;crews+=n;if(units>250 || crews>free)goto failed;gp_army[10]+=(uint8_t)n;
complete:
    gp_request[0]=0;w(gp_request+2,free-crews);gp_dispatch();w(gp_sector+GP_POP,r(gp_sector+GP_POP)-crews);return 1;
failed:
    for(age=9;age>=0;--age)if(gp_army[age])refund((uint16_t)age,gp_army[age]);
nuclear:
    if(fallback==8 && take(1,8)) {for(i=0;i<11;++i)gp_army[i]=0;gp_army[8]=1;return 1;}
    return 0;
}

/* 11B9:1C9C: a hostile tower/army or an unoccupied neutral sector. */
uint16_t gp_hostile(uint16_t faction) {
    uint16_t owner,i;uint8_t found;owner=r(gp_sector+0x3fe);found=0;
    if(faction>=4)return 0;
    if(owner<4 && !(gp_alliances[faction]&(1<<owner)))return 1;
    for(i=0;i<4;++i)if((gp_request[30]&(1<<i)) && r(gp_sector+0x2f4+i*2)) {
        if(!(gp_alliances[faction]&(1<<i)))return 1;found=1;
    }
    return owner==4 && !found;
}
/* 0D24:1582: retreat loses 10..50% for the human and 5..10% for a
 * computer, with at least one casualty from every present weapon class. */
void gp_travel_losses(uint16_t faction) {
    uint16_t percent,n,i;
    gp_request[0]=7;w(gp_request+2,faction==r(gp_request+26)?41:6);gp_dispatch();
    percent=r(gp_request+12)+(faction==r(gp_request+26)?10:5);
    for(i=0;i<11;++i)if(gp_army[i]) {n=(uint16_t)(gp_army[i]*percent)/100;if(!n)n=1;gp_army[i]-=(uint8_t)n;}
}

/* 1471:0278: leaving an allied tower is safe even during combat. */
uint16_t gp_retreat(uint16_t faction) {
    uint16_t owner,i;owner=r(gp_sector+0x3fe);
    if(faction>=4)return 0;
    if(owner<4)return !(gp_alliances[faction]&(1<<owner));
    for(i=0;i<4;++i)if((gp_request[30]&(1<<i)) && r(gp_sector+0x2f4+i*2) && !(gp_alliances[faction]&(1<<i)))return 1;
    return 0;
}
/* 16B4:26AB: emergency mobilization spends only available equipment,
 * caps the force at 250 units and fills the remainder with unarmed people. */
uint16_t gp_max_army(uint16_t first,uint16_t last) {
    uint16_t free,crews,units,n,crew,i;int16_t age;
    free=r(gp_sector+GP_FREE);crews=0;units=0;
    for(i=0;i<11;++i)gp_army[i]=0;
    for(age=(int16_t)last;age>=(int16_t)first;--age)if(age!=8) {
        crew=r(gp_army_rules+44+(uint16_t)age*2);if(!crew)return 0;
        n=(free-crews)/crew;if(n>250-units)n=250-units;if(!n)goto complete;
        n=take(n,(uint16_t)age);gp_army[age]+=(uint8_t)n;units+=n;crews+=n*crew;
    }
    n=free-crews;if(n>250-units)n=250-units;gp_army[10]+=(uint8_t)n;units+=n;crews+=n;
complete:
    if(!units)return 0;
    gp_request[0]=0;w(gp_request+2,free-crews);gp_dispatch();w(gp_sector+GP_POP,r(gp_sector+GP_POP)-crews);return 1;
}

/* 16B4:06DD: emergency defence below fifteen percent tower health. */
uint16_t gp_sos(void) {
    uint16_t cap,owner,i;owner=r(gp_sector+0x3fe);
    if(owner>=4 || (gp_sector[0x448]&16))return 0;
    cap=r(gp_buildings+r(gp_sector+0x418)*2);
    if(!cap || (uint16_t)(r(gp_sector+0x3d6)*100)/cap>=15)return 0;
    for(i=0;i<4;++i)if((gp_request[30]&(1<<i)) && r(gp_sector+0x2f4+i*2) && !(gp_alliances[owner]&(1<<i)))return 1;
    return 0;
}
static uint16_t draw(uint16_t bound) {
    gp_request[0]=7;w(gp_request+2,bound);gp_dispatch();return r(gp_request+12);
}
/* Formation half of 16B4:0DB1. Resident code performs arrival after this
 * overlay has returned, since arrival may need a different disk bank. */
uint16_t gp_reinforce(void) {
    uint16_t owner,i,allied,enemy,percent,threshold;
    if(draw(100)>=r(gp_personality+0x22))return 0;
    owner=r(gp_sector+0x3fe);if(owner>=4)return 0;allied=0;enemy=0;
    for(i=0;i<4;++i)if(gp_request[30]&(1<<i)) {
        if(gp_alliances[owner]&(1<<i))allied+=r(gp_sector+0x3f4+i*2);
        else enemy+=r(gp_sector+0x3f4+i*2);
    }
    percent=draw(r(gp_personality+0x26)-r(gp_personality+0x24)+1)+r(gp_personality+0x24);
    threshold=(uint16_t)((uint16_t)(percent*enemy)+99)/100;
    if(allied>=threshold)return 0;
    if(gp_make_army(threshold-allied,0,10,65535))return 1;
    threshold=(uint16_t)((uint16_t)(r(gp_personality+0x24)*enemy)+99)/100;
    return gp_make_army(threshold-allied,0,10,65535);
}
