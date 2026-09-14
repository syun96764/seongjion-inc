from js import document, window, setInterval, clearInterval
from pyodide.ffi import create_proxy
from datetime import date, timedelta
import random, json

REGIONS = {
    "북아메리카": {"pop": 600, "x": 16, "y": 30, "links": ["남아메리카","유럽","동아시아"]},
    "남아메리카": {"pop": 440, "x": 31, "y": 68, "links": ["북아메리카","아프리카"]},
    "유럽": {"pop": 750, "x": 48, "y": 28, "links": ["북아메리카","아프리카","서아시아"]},
    "아프리카": {"pop": 1490, "x": 56, "y": 55, "links": ["유럽","남아메리카","서아시아"]},
    "서아시아": {"pop": 510, "x": 67, "y": 43, "links": ["유럽","아프리카","동아시아"]},
    "동아시아": {"pop": 2400, "x": 76, "y": 35, "links": ["북아메리카","서아시아","오세아니아"]},
    "오세아니아": {"pop": 46, "x": 89, "y": 72, "links": ["동아시아"]},
}
UPGRADES = {
    "air": {"name":"기류 탑승", "desc":"모든 지역의 냄새 확산 속도 증가", "base":6, "max":5},
    "travel": {"name":"교통망 침투", "desc":"새 지역으로 전파될 확률 증가", "base":8, "max":4},
    "linger": {"name":"잔류성 강화", "desc":"지역 대응으로 인한 감소를 억제", "base":7, "max":4},
    "stealth": {"name":"무취 위장", "desc":"세계 대응 연구 속도 감소", "base":10, "max":3},
}
class Game:
    def __init__(self):
        self.timer=None
        self.proxies=[]
        self.selected="동아시아"
        self.speed=1
        self.reset_state()
        self.build_static()
        self.bind()
        document.getElementById("loading").classList.add("hidden")

    def reset_state(self):
        self.running=False; self.ended=False; self.day=0; self.points=4; self.response=0.0
        self.levels={k:0 for k in UPGRADES}
        self.smell={k:0.0 for k in REGIONS}
        self.news=["세계 냄새 관측망이 정상 가동됐다."]
        self.dot=None

    def proxy(self, fn):
        p=create_proxy(fn); self.proxies.append(p); return p

    def build_static(self):
        mp=document.getElementById("map")
        for name,r in REGIONS.items():
            el=document.createElement("button"); el.className="region"; el.id="region-"+name
            el.style.left=f"{r['x']}%"; el.style.top=f"{r['y']}%"
            el.innerHTML=f"<b>{name}</b><small>{r['pop']}백만 명</small><span class='fill'><i></i></span>"
            mp.appendChild(el)
        choices=document.getElementById("choices")
        for name,tag in [("동아시아","고밀도 · 빠른 성장"),("유럽","연결 중심 · 균형형"),("오세아니아","고립 지역 · 도전형")]:
            b=document.createElement("button"); b.className="choice"+(" selected" if name==self.selected else "")
            b.dataset.region=name; b.innerHTML=f"<b>{name}</b><br><small>{tag}</small>"; choices.appendChild(b)
        self.render_upgrades()

    def bind(self):
        for el in document.querySelectorAll(".choice"):
            el.addEventListener("click",self.proxy(self.choose))
        document.getElementById("start").addEventListener("click",self.proxy(self.start))
        document.getElementById("reset").addEventListener("click",self.proxy(self.show_restart))
        document.getElementById("again").addEventListener("click",self.proxy(self.restart))
        for el in document.querySelectorAll(".speed"):
            el.addEventListener("click",self.proxy(self.set_speed))

    def choose(self,e):
        self.selected=e.currentTarget.dataset.region
        for el in document.querySelectorAll(".choice"): el.classList.remove("selected")
        e.currentTarget.classList.add("selected")

    def start(self,e=None):
        self.smell[self.selected]=3.0; self.running=True
        self.news.insert(0,f"{self.selected}에서 최초의 냄새 신호가 감지됐다.")
        document.getElementById("start-overlay").classList.add("hidden")
        self.render()
        if self.timer is None: self.timer=setInterval(self.proxy(self.tick),700)

    def restart(self,e=None):
        self.reset_state()
        document.getElementById("end-overlay").classList.add("hidden")
        document.getElementById("start-overlay").classList.remove("hidden")
        self.render()

    def show_restart(self,e=None):
        self.reset_state(); document.getElementById("start-overlay").classList.remove("hidden"); self.render()

    def set_speed(self,e):
        self.speed=int(e.currentTarget.dataset.speed)
        for el in document.querySelectorAll(".speed"): el.classList.remove("active")
        e.currentTarget.classList.add("active")

    def tick(self,*args):
        if not self.running or self.ended or self.speed==0:return
        for _ in range(self.speed): self.step()
        self.render()

    def step(self):
        self.day+=1
        growth=.21+self.levels["air"]*.075
        resist=max(.05,1-self.levels["linger"]*.16)
        old=dict(self.smell)
        for name,val in old.items():
            if val>0:
                saturation=1-val/100
                self.smell[name]=min(100,max(0,val+growth*(1+val*.047)*saturation-self.response*.0015*resist))
                chance=(.006+self.levels["travel"]*.005)*(1+min(val,70)/35)
                for linked in REGIONS[name]["links"]:
                    if old[linked]<=0 and random.random()<chance:
                        self.smell[linked]=.5
                        self.news.insert(0,f"{linked}에서 새로운 냄새 흔적이 보고됐다.")
        coverage=self.coverage()
        if coverage>4:
            rate=(.018+coverage*.0026)*(1-self.levels["stealth"]*.2)
            self.response=min(100,self.response+rate)
        if self.day%8==0:
            infected=sum(v>0 for v in self.smell.values())
            self.points+=max(1,infected//2)
        if random.random()<.055 and self.dot is None:self.spawn_dot()
        if self.day in (15,35,60,100):
            self.news.insert(0,{15:"SNS에 정체불명의 냄새 제보가 늘고 있다.",35:"각 지역이 공기 정화 공동 대응을 시작했다.",60:"국제 냄새 연구팀이 분석 속도를 높였다.",100:"세계 교통망이 냄새 검사를 강화했다."}[self.day])
        if coverage>=99.8:self.finish(True)
        elif self.response>=100:self.finish(False)

    def coverage(self):
        total=sum(r["pop"] for r in REGIONS.values())
        return sum(REGIONS[k]["pop"]*v/100 for k,v in self.smell.items())/total*100

    def cost(self,key):
        u=UPGRADES[key]; return u["base"]+self.levels[key]*(u["base"]//2+2)

    def buy(self,e):
        key=e.currentTarget.dataset.key; u=UPGRADES[key]
        c=self.cost(key)
        if self.points>=c and self.levels[key]<u["max"]:
            self.points-=c; self.levels[key]+=1
            self.news.insert(0,f"{u['name']} 연구가 {self.levels[key]}단계에 도달했다.")
            self.render()

    def render_upgrades(self):
        box=document.getElementById("upgrades"); box.innerHTML=""
        for key,u in UPGRADES.items():
            lv=self.levels[key]; cost=self.cost(key)
            b=document.createElement("button"); b.className="upgrade"; b.dataset.key=key
            b.disabled=lv>=u["max"] or self.points<cost
            price="완료" if lv>=u["max"] else f"{cost} P"
            b.innerHTML=f"<div class='row'><b>{u['name']} <span class='level'>LV.{lv}</span></b><em>{price}</em></div><small>{u['desc']}</small>"
            b.addEventListener("click",self.proxy(self.buy)); box.appendChild(b)

    def spawn_dot(self):
        infected=[k for k,v in self.smell.items() if v>0]
        if not infected:return
        name=random.choice(infected); r=REGIONS[name]
        d=document.createElement("button"); d.className="event-dot"; d.textContent="+"
        d.style.left=f"{r['x']+random.randint(-5,5)}%"; d.style.top=f"{r['y']+random.randint(-7,7)}%"
        d.addEventListener("click",self.proxy(self.collect)); document.getElementById("map").appendChild(d); self.dot=d

    def collect(self,e):
        gain=random.randint(3,7); self.points+=gain
        e.currentTarget.remove(); self.dot=None
        self.news.insert(0,f"냄새 포인트 {gain}점을 회수했다."); self.render()

    def finish(self,won):
        self.ended=True; self.running=False
        ov=document.getElementById("end-overlay"); ov.classList.remove("hidden")
        document.getElementById("end-kicker").textContent="MISSION COMPLETE" if won else "RESPONSE COMPLETE"
        document.getElementById("end-title").textContent="전 세계 확산 완료" if won else "세계 대응망 가동"
        document.getElementById("end-copy").textContent=(f"{self.day}일 만에 모든 지역의 냄새 점유가 완료됐다." if won else f"{self.day}일째 세계 대응 지수가 먼저 100%에 도달했다. 업그레이드 순서를 바꿔 다시 시도해 보자.")

    def render(self):
        cov=self.coverage()
        document.getElementById("points").textContent=str(self.points)
        document.getElementById("days").textContent=str(self.day)
        document.getElementById("coverage").textContent=f"{cov:.1f}%"
        document.getElementById("response").textContent=f"{self.response:.1f}%"
        document.getElementById("coverage-bar").style.width=f"{cov}%"
        document.getElementById("response-bar").style.width=f"{self.response}%"
        document.getElementById("date").textContent=(date(2026,9,14)+timedelta(days=self.day)).strftime("%Y.%m.%d")
        rows=[]
        for name,val in self.smell.items():
            el=document.getElementById("region-"+name)
            el.className="region"+(" infected" if val>0 else "")+(" hot" if val>=65 else "")
            el.querySelector(".fill i").style.width=f"{val}%"
            rows.append(f"<div class='regional-row'><span>{name}</span><span class='bar'><i style='width:{val}%'></i></span><b>{val:.0f}%</b></div>")
        document.getElementById("regional").innerHTML="".join(rows)
        feed=document.getElementById("feed")
        feed.innerHTML="".join(f"<div class='news'><time>DAY {max(0,self.day-i)}</time>{n}</div>" for i,n in enumerate(self.news[:9]))
        self.render_upgrades()

game=Game()
