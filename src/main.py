# -*- coding: utf-8 -*-

# Nicolas, 2021-03-05
from __future__ import absolute_import, print_function, unicode_literals

import random
from sysconfig import get_path 
import numpy as np
import sys
from itertools import chain
import time

from tqdm import tqdm

import pygame

from pySpriteWorld.gameclass import Game,check_init_game_done
from pySpriteWorld.spritebuilder import SpriteBuilder
from pySpriteWorld.players import Player
from pySpriteWorld.sprite import MovingSprite
from pySpriteWorld.ontology import Ontology
import pySpriteWorld.glo

from search.grid2D import ProblemeGrid2D
from search import probleme

# ---- ---- ---- ---- ---- ----
# ---- Main                ----
# ---- ---- ---- ---- ---- ----

game = Game()

def init(_boardname=None):
    global player,game
    name = _boardname if _boardname is not None else 'mini-quoridorMap'
    game = Game('./Cartes/' + name + '.json', SpriteBuilder)
    game.O = Ontology(True, 'SpriteSheet-32x32/tiny_spritesheet_ontology.csv')
    game.populate_sprite_names(game.O)
    game.fps = 5  # frames per second
    game.mainiteration()
    player = game.player
    
def main():
    resultats = []
    for partie in tqdm(range(100)):

        #for arg in sys.argv:
        iterations = 100 # default
        if len(sys.argv) == 2:
            iterations = int(sys.argv[1])
        #print ("Iterations: ")
        print (iterations)

        init()
        

        
        #-------------------------------
        # Initialisation
        #-------------------------------
        
        nbLignes = game.spriteBuilder.rowsize
        #print(nbLignes)

        nbCols = game.spriteBuilder.colsize
        #print(nbCols)
        assert nbLignes == nbCols # a priori on souhaite un plateau carre
        lMin=2  # les limites du plateau de jeu (2 premieres lignes utilisees pour stocker les murs)
        lMax=nbLignes-2 
        cMin=2
        cMax=nbCols-2
    
        
        players = [o for o in game.layers['joueur']]
        nbPlayers = len(players)
        
        
        # on localise tous les états initiaux (loc du joueur)
        # positions initiales des joueurs
        initStates = [o.get_rowcol() for o in players]
        ligneObjectif = (initStates[1][0],initStates[0][0]) # chaque joueur cherche a atteindre la ligne ou est place l'autre 
        #print(ligneObjectif)
        
        # on localise tous les murs
        # sur le layer ramassable    
        walls = [[],[]]
        walls[0] = [o for o in game.layers['ramassable'] if (o.get_rowcol()[0] == 0 or o.get_rowcol()[0] == 1)]  
        walls[1] = [o for o in game.layers['ramassable'] if (o.get_rowcol()[0] == nbLignes-2 or o.get_rowcol()[0] == nbLignes-1)]  
        
        allWalls = walls[0]+walls[1]
        nbWalls = len(walls[0])
        assert len(walls[0])==len(walls[1]) # les 2 joueurs doivent avoir le mm nombre de murs
        
        ################################################ MANIPULATION JEU  #######################################
        #-------------------------------
        # Fonctions permettant de récupérer les listes des coordonnées
        # d'un ensemble d'objets murs ou joueurs
        #-------------------------------
        
        def wallStates(walls): 
            # donne la liste des coordonnees dez murs
            return [w.get_rowcol() for w in walls]
        
        def playerStates(players):
            # donne la liste des coordonnees dez joueurs
            return [p.get_rowcol() for p in players]
        
            
        #-------------------------------
        # On choisit une case objectif au hasard pour chaque joueur
        #-------------------------------
        
        allObjectifs = ([(ligneObjectif[0],i) for i in range(cMin,cMax)],[(ligneObjectif[1],i) for i in range(cMin,cMax)])
        objectifs =  (allObjectifs[0][random.randint(cMin,cMax-3)], allObjectifs[1][random.randint(cMin,cMax-3)])

        #-------------------------------
        # Fonctions definissant les positions legales et placement de mur aléatoire
        #-------------------------------
        def check_path(player,p_pos,pos,temp_w):
            row,col=pos
            g =np.ones((nbLignes,nbCols),dtype=bool)  # une matrice remplie par defaut a True  
            for w in temp_w:            # on met False quand murs
                g[w]=False
            g[row][col] = False # on rajoute le positionenement du nouveau mur
            for i in range(nbLignes):                 # on exclut aussi les bordures du plateau
                g[0][i]=False
                g[1][i]=False
                g[nbLignes-1][i]=False
                g[nbLignes-2][i]=False
                g[i][0]=False
                g[i][1]=False
                g[i][nbLignes-1]=False
                g[i][nbLignes-2]=False
            p = ProblemeGrid2D(p_pos[player],objectifs[player],g,'manhattan')
            path = probleme.astar(p,verbose=False)
            return path[-1]==objectifs[player] 

        def legal_wall_position(player,p_pos,pos,temp_w):
            row,col = pos

            if col>=9 or row >=9 or col <2 or row <2:

                return False
            if ((pos not in wallStates(allWalls)) and (pos not in playerStates(players)) and row>lMin and row<lMax-1 and col>=cMin and col<cMax):

                return check_path(1-player,p_pos,pos,temp_w) and check_path(player,p_pos,pos,temp_w)
            return False
        
        def draw_random_wall_location(player,p_pos):
            while True:
                temp_w= wallStates(allWalls)
                random_loc = (random.randint(lMin,lMax),random.randint(cMin,cMax))
                if legal_wall_position(player,p_pos,random_loc,temp_w):
                    temp_w.append(random_loc)
                    inc_pos =[(0,1),(0,-1),(1,0),(-1,0)] 
                    random.shuffle(inc_pos)
                    for w in inc_pos:
                        random_loc_bis = (random_loc[0] + w[0],random_loc[1]+w[1])
                        if legal_wall_position(player,p_pos,random_loc_bis,temp_w):
                            return(random_loc,random_loc_bis)

        def get_Path(player,p_pos,type):
        
            g =np.ones((nbLignes,nbCols),dtype=bool)  # une matrice remplie par defaut a True  
            for w in wallStates(allWalls):            # on met False quand murs
                g[w]=False
            for i in range(nbLignes):                 # on exclut aussi les bordures du plateau
                g[0][i]=False
                g[1][i]=False
                g[nbLignes-1][i]=False
                g[nbLignes-2][i]=False
                g[i][0]=False
                g[i][1]=False
                g[i][nbLignes-1]=False
                g[i][nbLignes-2]=False
            p = ProblemeGrid2D(p_pos[player],objectifs[player],g,'manhattan')
            path = probleme.astar(p,verbose=False)
            
            if type:
                for obj in allObjectifs[player]:
                    p = ProblemeGrid2D(p_pos[player],obj,g,'manhattan')
                    path_dynamique = probleme.astar(p,verbose=False)
                    if len(path_dynamique) < len(path):
                        path = path_dynamique
        
            return path
        def gagnant(p_pos,type):
            if type:

                if  p_pos[0] in allObjectifs[0]:
                    return (True,0)
                if p_pos[1] in allObjectifs[1]:
                    return (True,1)
            if not type:
                if p_pos[0]==objectifs[0]:
                    return (True,0)
                if p_pos[1]==objectifs[1]:
                    return(True,1)
            return (False,3)
        
        def strategic_walls(player,p_pos,mode):
            opponent_id = 1-player
            path_opponent= get_Path(opponent_id,p_pos,mode)
            path_opponent= path_opponent[1:]
            path_opponent_=path_opponent
            
            for i in path_opponent_:
                inc_pos =[(0,1),(0,-1),(1,0),(-1,0)] 
                random.shuffle(inc_pos)
                for j in inc_pos:
                    wall_1= (i[0]+j[0],i[1]+j[1])
                    tp=pd_walls
                    tp.append(wall_1)
                    if legal_wall_position(player,p_pos,wall_1,tp):
                        pd_walls.append(wall_1)
                        final=(i,wall_1)
                        return final
            return 0
        ################################################ END MANIPULATION JEU  ####################################
        
        ###################################################### BASE ###############################################
        def game_base():                
            #time.sleep(3)       
            for i in range(0,len(walls[0]),2): 
                ((x1,y1),(x2,y2)) = draw_random_wall_location()
                walls[0][i].set_rowcol(x1,y1)
                walls[0][i+1].set_rowcol(x2,y2)
                #time.sleep(3)
                game.mainiteration()
            #-------------------------------
            # calcul A* pour le joueur 1
            #-------------------------------
            g =np.ones((nbLignes,nbCols),dtype=bool)  # une matrice remplie par defaut a True  
            for w in wallStates(allWalls):            # on met False quand murs
                g[w]=False
            for i in range(nbLignes):                 # on exclut aussi les bordures du plateau
                g[0][i]=False
                g[1][i]=False
                g[nbLignes-2][i]=False #was 1
                g[nbLignes-2][i]=False
                g[i][0]=False
                g[i][1]=False
                g[i][nbLignes-1]=False
                g[i][nbLignes-2]=False
            p = ProblemeGrid2D(initStates[1],objectifs[1],g,'manhattan')
            path = probleme.astar(p,verbose=False)
            #-------------------------------
            # Boucle principale de déplacements 
            #------------------------------   
            p_pos = initStates
            for i in range(iterations):
                # on fait bouger le joueur 1 jusqu'à son but
                # en suivant le chemin trouve avec A* 
                row,col = path[i]
                p_pos[1]=(row,col)
                players[1].set_rowcol(row,col)
                if (row,col) == objectifs[1]:
                    break
                game.mainiteration()
            pygame.quit()
    
        ###################################################### END BASE #################################################
        
        ###################################################### STRATEGIES ###############################################
        
        def aleatoire(player,pd_walls,type):
            """
            choix 1: il doit placer un mur
            choix 0 : se deplace
            """
            choix=random.choice([0,1])
            if choix:
                if pd_walls[player]<=8:
                    next_wall=pd_walls[player]
                    ((x1,y1),(x2,y2)) = draw_random_wall_location(player, p_pos)
                    #((x1,y1),(x2,y2))= strategic_walls(player,p_pos,pd_walls)
                    walls[player][next_wall].set_rowcol(x1,y1)
                    walls[player][next_wall+1].set_rowcol(x2,y2)
                    pd_walls[player]=pd_walls[player]+2
                else:
                    choix=0
            if not choix:
                path= get_Path(player,p_pos,type)
                if len(path)>1:
                    row,col = path[1]
                    p_pos[player]=(row,col)
                    players[player].set_rowcol(row,col)
                else:
                    return 5
            return choix

        def stochastique(player, pd_walls, lastMove, strategies):
            prob = [random.randint(0, 100) for i in range(0, len(strategies))]
            s = sum(prob)
            prob = [i / s for i in prob]
            choix = np.random.choice(strategies, p=prob)
            if choix == titFortat or choix == strat_block_it:
                return choix(player, pd_walls, type,lastMove)
            else:
                return choix(player, pd_walls,type)      
                
        
        def titFortat(player, pd_walls,type,lastMove = False):
            
            if not lastMove:
                path= get_Path(player,p_pos,type)
                row,col = path[1]
                p_pos[player]=(row,col)
                players[player].set_rowcol(row,col)
                return 0
            
            if lastMove:
                if pd_walls[player]<=8:
                    next_wall=pd_walls[player]
                    ((x1,y1),(x2,y2)) = draw_random_wall_location(player, p_pos)
                    walls[player][next_wall].set_rowcol(x1,y1)
                    walls[player][next_wall+1].set_rowcol(x2,y2)
                    pd_walls[player]=pd_walls[player]+2
                    return 1
                else:
                    path= get_Path(player,p_pos,type)
                    if len(path)>1:
                        row,col = path[1]
                        p_pos[player]=(row,col)
                        players[player].set_rowcol(row,col)
                    else:
                        return 5
            
        def walk(player,pd_walls,type):
            path= get_Path(player,p_pos,type)
            if len(path)>1:
                row,col = path[1]
                p_pos[player]=(row,col)
                players[player].set_rowcol(row,col)
            else:
                return 5
            return 0
        
        def strat_block_it(player, placed_walls, mode,last_adv):
            """
            ====================================================================================
            Stratégie block it sans left

            ARGUMENTS 
            le joueur <player> applique la stratégie 
            La variable placed_walls contient les murs deja posés par <player>
            La variable last_adv contient le dernier CHOIX de l'adversaire (mur ou deplacer) 
                si c'est l'ouverture et que le joueur en face n'a pas encore joué, alors last_adv == None
            itera est le tour courant dans la partie 
            
            RETOUR 
            Cette fonction retourne un tuple 
            choice
            # -----------------------

            # """
            # position du joueur 
            pos_player = p_pos[player]
            (lig_jo,col_jo) = pos_player
            # position de l'adverse 
            opponent_id= 1 if player == 0 else 0 
            (lig_adv,col_adv) = p_pos[opponent_id]
            pos_adv = (lig_adv,col_adv)
            # traduction du last_adv : 
            if last_adv == 1 :
                last_adv = "mur"
            else : 
                last_adv = "deplacer"
            # ---------------------------------------------------------------------------------------------------------------------------
            # CAS OU player est le premier à jouer ou alors l'adversaire a placé un mur 
            # player se déplace donc selon A*
            if last_adv == None or last_adv == False or last_adv == "mur" :
                # on definit le chemin avec A*
                path= get_Path(player,p_pos,mode)
                row,col = path[1]
                p_pos[player]=(row,col)
                players[player].set_rowcol(row,col)
                return 0
            # ---------------------------------------------------------------------------------------------------------------------------
            # CAS ou le player s'est déplacé au tour precedent :
            # player place donc un mur DEVANT l'adversaire 
            elif last_adv == "deplacer" :
                # ASSEZ DE MURS 
                if placed_walls[player]<=8: 
                    next_wall=placed_walls[player]
                    block =strategic_walls(player,p_pos,mode)
                    # si on peut pas poser de mur devant, on en pose un au hasard
                    if not block:
                        ((x1,y1),(x2,y2))= draw_random_wall_location(player,p_pos)
                    # sinon, on pose un mur devant l'adversaire selon A*
                    else:
                        ((x1,y1),(x2,y2))= block
                    walls[player][next_wall].set_rowcol(x1,y1)
                    walls[player][next_wall+1].set_rowcol(x2,y2)
                    placed_walls[player]=placed_walls[player]+2
                    return 1
                # PLUS ASSEZ DE MURS DONC ON SE DEPLACE 
                else:
                    # on definit le chemin avec A*
                    path= get_Path(player,p_pos,mode)
                    row,col = path[1]
                    p_pos[player]=(row,col)
                    players[player].set_rowcol(row,col)
                
                    return 0
        
        ################################################ JEU  ####################################

        pd_walls=[0,0]
        p_pos=initStates
        j=random.choice([0,1])
        player=j    

        type=1
        j_1 = 0
        j_2 = 0
        lastMove = False
        strategies = [walk,aleatoire,titFortat,strat_block_it]
        for i in range(iterations):
            if player == 0:
                lastMove = titFortat(player, pd_walls,type,lastMove)
                #stochastique(player, pd_walls, lastMove, strategies)
                #walk(player, pd_walls, type)
                #strat_block_it(player, pd_walls, type,last_adv)
            else:
                lastMove = stochastique(player, pd_walls, lastMove, strategies)
                
            a=gagnant(p_pos,type)
            if a[0] or lastMove==5:
                print("Gagnant player, ",a[1])
                game.mainiteration()
                break
            player = 1 if player == 0 else 0 
            game.mainiteration()
 
 
    
        
        if a[1] == 0:
            j_1 += 1
        else:
            j_2 += 1
        
        resultats.append([j_1, j_2])

    pygame.quit()
    print(resultats)
    print
    np.savetxt("Scores_titFortat_stochastique.csv", resultats, delimiter=";")      


        
    
    
   

if __name__ == '__main__':
    main()
    


