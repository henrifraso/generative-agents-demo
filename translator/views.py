"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""
import os
import string
import random
import json
from os import listdir
import os
import uuid
import time

import datetime
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from global_methods import *

from django.templatetags.static import static
from .models import *

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def landing(request):
  context = {}
  template = "landing/landing.html"
  return render(request, template, context)


def _resolve_sim_code(sim_code):
  cs = os.path.join(_BASE, "compressed_storage")
  if os.path.isdir(os.path.join(cs, sim_code)):
    return sim_code
  for name in os.listdir(cs):
    if name.lower() == sim_code.lower():
      return name
  return sim_code

def demo(request, sim_code, step, play_speed="2"):
  sim_code = _resolve_sim_code(sim_code)
  move_file = os.path.join(_BASE, "compressed_storage", sim_code, "master_movement.json")
  meta_file = os.path.join(_BASE, "compressed_storage", sim_code, "meta.json")
  step = int(step)
  play_speed_opt = {"1": 1, "2": 2, "3": 4,
                    "4": 8, "5": 16, "6": 32}
  if play_speed not in play_speed_opt: play_speed = 2
  else: play_speed = play_speed_opt[play_speed]

  # Loading the basic meta information about the simulation.
  meta = dict() 
  with open (meta_file) as json_file: 
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00", 
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step): 
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # Loading the movement file
  raw_all_movement = dict()
  with open(move_file) as json_file: 
    raw_all_movement = json.load(json_file)
 
  # Loading all names of the personas
  persona_names = dict()
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()): 
    persona_names += [{"original": p, 
                       "underscore": p.replace(" ", "_"), 
                       "initial": p[0] + p.split(" ")[-1][0]}]
    persona_names_set.add(p)

  # <all_movement> is the main movement variable that we are passing to the 
  # frontend. Whereas we use ajax scheme to communicate steps to the frontend
  # during the simulation stage, for this demo, we send all movement 
  # information in one step. 
  all_movement = dict()

  # Preparing the initial step. 
  # <init_prep> sets the locations and descriptions of all agents at the
  # beginning of the demo determined by <step>. 
  init_prep = dict() 
  for int_key in range(step+1): 
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set: 
      if p in val: 
        init_prep[p] = val[p]
  persona_init_pos = dict()
  for p in persona_names_set: 
    persona_init_pos[p.replace(" ","_")] = init_prep[p]["movement"]
  all_movement[step] = init_prep

  # Finish loading <all_movement>
  for int_key in range(step+1, len(raw_all_movement.keys())): 
    all_movement[int_key] = raw_all_movement[str(int_key)]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": json.dumps(persona_init_pos), 
             "all_movement": json.dumps(all_movement), 
             "start_datetime": start_datetime,
             "sec_per_step": sec_per_step,
             "play_speed": play_speed,
             "mode": "demo"}
  template = "demo/demo.html"

  return render(request, template, context)


def UIST_Demo(request): 
  return demo(request, "March20_the_ville_n25_UIST_RUN-step-1-141", 2160, play_speed="3")


def home(request):
  f_curr_sim_code = "temp_storage/curr_sim_code.json"
  f_curr_step = "temp_storage/curr_step.json"

  if not check_if_file_exists(f_curr_step): 
    context = {}
    template = "home/error_start_backend.html"
    return render(request, template, context)

  with open(f_curr_sim_code) as json_file:  
    sim_code = json.load(json_file)["sim_code"]
  
  with open(f_curr_step) as json_file:  
    step = json.load(json_file)["step"]

  os.remove(f_curr_step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"storage/{sim_code}/personas", ""): 
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      file_count += [int(x.split(".")[0])]
  curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step, 
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos,
             "mode": "simulate"}
  template = "home/home.html"
  return render(request, template, context)


def replay(request, sim_code, step): 
  sim_code = sim_code
  step = int(step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"storage/{sim_code}/personas", ""): 
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      file_count += [int(x.split(".")[0])]
  curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos, 
             "mode": "replay"}
  template = "home/home.html"
  return render(request, template, context)


def replay_persona_state(request, sim_code, step, persona_name): 
  sim_code = sim_code
  step = int(step)

  persona_name_underscore = persona_name
  persona_name = " ".join(persona_name.split("_"))
  memory = os.path.join(_BASE, "storage", sim_code, "personas", persona_name, "bootstrap_memory")
  if not os.path.exists(memory):
    memory = os.path.join(_BASE, "compressed_storage", sim_code, "personas", persona_name, "bootstrap_memory")

  with open(memory + "/scratch.json") as json_file:  
    scratch = json.load(json_file)

  with open(memory + "/spatial_memory.json") as json_file:  
    spatial = json.load(json_file)

  with open(memory + "/associative_memory/nodes.json") as json_file:  
    associative = json.load(json_file)

  a_mem_event = []
  a_mem_chat = []
  a_mem_thought = []

  for count in range(len(associative.keys()), 0, -1): 
    node_id = f"node_{str(count)}"
    node_details = associative[node_id]

    if node_details["type"] == "event":
      a_mem_event += [node_details]

    elif node_details["type"] == "chat":
      a_mem_chat += [node_details]

    elif node_details["type"] == "thought":
      a_mem_thought += [node_details]
  
  context = {"sim_code": sim_code,
             "step": step,
             "persona_name": persona_name, 
             "persona_name_underscore": persona_name_underscore, 
             "scratch": scratch,
             "spatial": spatial,
             "a_mem_event": a_mem_event,
             "a_mem_chat": a_mem_chat,
             "a_mem_thought": a_mem_thought}
  template = "persona_state/persona_state.html"
  return render(request, template, context)


def path_tester(request):
  context = {}
  template = "path_tester/path_tester.html"
  return render(request, template, context)


def process_environment(request): 
  """
  <FRONTEND to BACKEND> 
  This sends the frontend visual world information to the backend server. 
  It does this by writing the current environment representation to 
  "storage/environment.json" file. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  environment = data["environment"]

  with open(f"storage/{sim_code}/environment/{step}.json", "w") as outfile:
    outfile.write(json.dumps(environment, indent=2))

  return HttpResponse("received")


def update_environment(request): 
  """
  <BACKEND to FRONTEND> 
  This sends the backend computation of the persona behavior to the frontend
  visual server. 
  It does this by reading the new movement information from 
  "storage/movement.json" file.

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]

  response_data = {"<step>": -1}
  if (check_if_file_exists(f"storage/{sim_code}/movement/{step}.json")):
    with open(f"storage/{sim_code}/movement/{step}.json") as json_file: 
      response_data = json.load(json_file)
      response_data["<step>"] = step

  return JsonResponse(response_data)


# ═══════════════════════════════════════════════════════
# MULTIPLAYER — estado em memória (sem banco de dados)
# ═══════════════════════════════════════════════════════
_ROOMS = {}
_MP_SPAWNS = [(70,50),(72,50),(68,50),(70,52),(72,52)]

def _mp_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def _mp_clean():
    now = time.time()
    for k in [k for k, v in _ROOMS.items() if now - v.get('ts', 0) > 3600]:
        del _ROOMS[k]

@csrf_exempt
def mp_room_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try: data = json.loads(request.body)
    except: data = {}
    name = str(data.get('name', 'Player'))[:20]
    _mp_clean()
    code = _mp_code()
    while code in _ROOMS: code = _mp_code()
    pid = str(uuid.uuid4())[:8]
    sp = _MP_SPAWNS[0]
    _ROOMS[code] = {
        'ts': time.time(), 'started': False, 'creator': pid,
        'players': {
            pid: {'name': name, 'x': sp[0]*32+16, 'y': sp[1]*32+16,
                  'dir': 'down', 'action': '', 'ts': time.time()}
        },
        'farm': {
            'plots': [{'state': 'empty', 'timer': 0} for _ in range(6)],
            'warehouse': 0,
            'kitchen': {'cooking': False, 'timer': 0, 'count': 0},
            'fridge': 0,
        },
        'following': {},
        'msgs': [], 'seq': 0,
    }
    return JsonResponse({'room_code': code, 'player_id': pid})

@csrf_exempt
def mp_room_join(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try: data = json.loads(request.body)
    except: data = {}
    code = str(data.get('room_code', '')).upper().strip()
    name = str(data.get('name', 'Player'))[:20]
    if code not in _ROOMS:
        return JsonResponse({'error': 'Sala não encontrada'}, status=404)
    room = _ROOMS[code]
    if room['started']:
        return JsonResponse({'error': 'Partida já iniciada'}, status=400)
    pid = str(uuid.uuid4())[:8]
    idx = len(room['players'])
    sp = _MP_SPAWNS[min(idx, 4)]
    room['players'][pid] = {
        'name': name, 'x': sp[0]*32+16, 'y': sp[1]*32+16,
        'dir': 'down', 'action': '', 'ts': time.time()
    }
    players = [{'id': k, 'name': v['name']} for k, v in room['players'].items()]
    return JsonResponse({'player_id': pid, 'players': players, 'creator': room['creator']})

@csrf_exempt
def mp_room_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try: data = json.loads(request.body)
    except: data = {}
    code = str(data.get('room_code', '')).upper()
    pid = str(data.get('player_id', ''))
    if code not in _ROOMS:
        return JsonResponse({'error': 'Sala não encontrada'}, status=404)
    room = _ROOMS[code]
    if room['creator'] != pid:
        return JsonResponse({'error': 'Só o criador pode iniciar'}, status=403)
    room['started'] = True
    return JsonResponse({'ok': True})

@csrf_exempt
def mp_sync(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try: data = json.loads(request.body)
    except: return JsonResponse({'error': 'JSON inválido'}, status=400)
    code = str(data.get('room_code', '')).upper()
    pid = str(data.get('player_id', ''))
    if code not in _ROOMS:
        return JsonResponse({'error': 'Sala não encontrada'}, status=404)
    room = _ROOMS[code]
    now = time.time()
    # Atualizar estado do jogador
    if pid in room['players']:
        p = room['players'][pid]
        p['x'] = data.get('x', p['x'])
        p['y'] = data.get('y', p['y'])
        p['dir'] = data.get('dir', p['dir'])
        p['action'] = data.get('action', '')
        p['ts'] = now
    # Atualizar farm compartilhado
    if isinstance(data.get('farm'), dict):
        fd = data['farm']
        if isinstance(fd.get('plots'), list): room['farm']['plots'] = fd['plots']
        if 'warehouse' in fd: room['farm']['warehouse'] = int(fd['warehouse'])
        if isinstance(fd.get('kitchen'), dict): room['farm']['kitchen'] = fd['kitchen']
        if 'fridge' in fd: room['farm']['fridge'] = int(fd['fridge'])
    # Following compartilhado
    if isinstance(data.get('following'), dict):
        room['following'] = data['following']
    # Nova mensagem de chat
    if data.get('msg'):
        pname = room['players'].get(pid, {}).get('name', '?')
        room['msgs'].append({'seq': room['seq'], 'who': pname, 'text': str(data['msg'])[:200]})
        room['seq'] += 1
        if len(room['msgs']) > 50: room['msgs'] = room['msgs'][-50:]
    # Remover jogadores inativos (>15s)
    for sp_id in [k for k, v in room['players'].items() if now - v['ts'] > 15]:
        del room['players'][sp_id]
    # Mensagens novas para o cliente
    last_seq = int(data.get('last_seq', -1))
    new_msgs = [m for m in room['msgs'] if m['seq'] > last_seq]
    # Resposta
    players_out = {}
    for i, (k, v) in enumerate(room['players'].items()):
        players_out[k] = {'name': v['name'], 'x': v['x'], 'y': v['y'], 'dir': v['dir'], 'ci': i}
    return JsonResponse({
        'started': room['started'],
        'creator': room['creator'],
        'players': players_out,
        'farm': room['farm'],
        'following': room['following'],
        'new_msgs': new_msgs,
        'player_count': len(room['players']),
    })


def path_tester_update(request):
  """
  Processing the path and saving it to path_tester_env.json temp storage for 
  conducting the path tester. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  data = json.loads(request.body)
  camera = data["camera"]

  with open(f"temp_storage/path_tester_env.json", "w") as outfile:
    outfile.write(json.dumps(camera, indent=2))

  return HttpResponse("received")









