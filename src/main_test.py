# -*- coding: utf-8 -*-

# Nicolas, 2021-03-05
from __future__ import absolute_import, print_function, unicode_literals

import random 
import numpy as np
import sys
from itertools import chain


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

    #for arg in sys.argv:
    iterations = 100 # default
    if len(sys.argv) == 2:
        iterations = int(sys.argv[1])
    print ("Iterations: ")
    print (iterations)

    init()
    

    
    #-------------------------------
    # Initialisation
    #-------------------------------
    
    nbLignes = game.spriteBuilder.rowsize
    nbCols = game.spriteBuilder.colsize
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
    
    # on localise tous les murs
    # sur le layer ramassable    
    walls = [[],[]]
    walls[0] = [o for o in game.layers['ramassable'] if (o.get_rowcol()[0] == 0 or o.get_rowcol()[0] == 1)]  
    walls[1] = [o for o in game.layers['ramassable'] if (o.get_rowcol()[0] == nbLignes-2 or o.get_rowcol()[0] == nbLignes-1)]  
    allWalls = walls[0]+walls[1]
    nbWalls = len(walls[0])
    assert len(walls[0])==len(walls[1]) # les 2 joueurs doivent avoir le mm nombre de murs
    
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
    # Rapport de ce qui est trouve sut la carte
    #-------------------------------
    print("lecture carte")
    print("-------------------------------------------")
    print("lignes", nbLignes)
    print("colonnes", nbCols)
    print("Trouvé ", nbPlayers, " joueurs avec ", int(nbWalls/2), " murs chacun" )
    print ("Init states:", initStates)
    print("-------------------------------------------")

    #-------------------------------
    # Carte demo 
    # 2 joueurs 
    # Joueur 0: place au hasard
    # Joueur 1: A*
    #-------------------------------
    
        
    #-------------------------------
    # On choisit une case objectif au hasard pour chaque joueur
    #-------------------------------
    
    allObjectifs = ([(ligneObjectif[0],i) for i in range(cMin,cMax)],[(ligneObjectif[1],i) for i in range(cMin,cMax)])
    print("Tous les objectifs joueur 0", allObjectifs[0])
    print("Tous les objectifs joueur 1", allObjectifs[1])
    objectifs =  (allObjectifs[0][random.randint(cMin,cMax-3)], allObjectifs[1][random.randint(cMin,cMax-3)])
    print("Objectif joueur 0 choisi au hasard", objectifs[0])
    print("Objectif joueur 1 choisi au hasard", objectifs[1])

    #-------------------------------
    # Fonctions definissant les positions legales et placement de mur aléatoire
    #-------------------------------
    
    def legal_wall_position(pos):
        row,col = pos
        # une position legale est dans la carte et pas sur un mur deja pose ni sur un joueur
        # attention: pas de test ici qu'il reste un chemin vers l'objectif
        return ((pos not in wallStates(allWalls)) and (pos not in playerStates(players)) and row>lMin and row<lMax-1 and col>=cMin and col<cMax)
    
    def draw_random_wall_location():
        # tire au hasard un couple de position permettant de placer un mur
        while True:
            random_loc = (random.randint(lMin,lMax),random.randint(cMin,cMax))
            if legal_wall_position(random_loc):  
                inc_pos =[(0,1),(0,-1),(1,0),(-1,0)] 
                random.shuffle(inc_pos)
                for w in inc_pos:
                    random_loc_bis = (random_loc[0] + w[0],random_loc[1]+w[1])
                    if legal_wall_position(random_loc_bis):
                        return(random_loc,random_loc_bis)
                    
    
    def strat_block_it(joueur,joueur_adv,pos_joueur, pos_adv,last_adv, nb_gauche):
        """
        ====================================================================================
        Stratégie block it 
        le joueur <joueur> applique la stratégie 
        La variable pos_adv contient la position de l'adversaire 
        La variable last_adv contient le dernier CHOIX de l'adversaire (mur ou deplacer) 
            si c'est l'ouverture et que le joueur en face n'a pas encore joué, alors last_adv == None


        
        Cette fonction retourne un tuple {choix, mur, position}. Les return possibles sont :
        -----------------------
        => {choix : "mur", mur : M1, deplacer : None}
        c'est le premier mur placé par le joueur, soit 
            - après le premier deplacement du joueur adversaire, tour 2 
            - au tour 1 

        -----------------------
        => {choix : "mur", mur : position du mur, deplacer : None}
        c'est le cas ou le joueur pose un mur de sa rangée de mur pour bloquer l'adversaire

        # -----------------------
        # => {choix : "deplacer", mur : None, deplacer : position ou le joueur se deplace}
        # c'est le cas ou le joueur se deplace 
        #     - ses 2 premiers deplacements sont vers la gauche (donc tant que nb_gauche > 0)
        #     - les deplacements suivants suivent A-STAR (si nb_gauche == 0)
        
        # -----------------------

        # """
        # # CAS D'OUVERTURE (depend de qui commence)

        # # cas ou notre joueur commence 
        # if last_adv == None:
        #     # notre joueur place le mur M1 qui est situé à gauche (ou a droite par rapport au joueur_adv) du joueur_adv
        #     lig_adv,col_adv = initStates[joueur_adv]
        #     posPlayers[1]=(row,col)
        #     players[1].set_rowcol(row,col)
                    

    
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
    
    # nombres de murs en reserves pour les joueurs 0 et 1 
    l1 = len(walls[0])
    l2 = len(walls[1])

    # nombres de murs posés par j0 (i) et j1 (k)
    i = 0
    k = 0

    # initialisation des variables de choix et de joueurs 
    jeu = ["mur","deplacer"]
    joueurs = ["j0","j1"]
    j = random.choice(joueurs)
    posPlayers = initStates
    print("Le joueur : ",j," va commencer")


    ########################################################################################
    ########################################################################################
    ################################ LANCEMENT DU JEU ######################################
    ########################################################################################
    ########################################################################################

    for a in range(iterations):
        # le joueur j0 joue :
        if j == "j0":
            #passage de main pour le tour suivant 
            j = "j1"

            choix = random.choice(jeu)
            p = ProblemeGrid2D(initStates[0],objectifs[0],g,'manhattan')
            path_j0 = probleme.astar(p,verbose=False)

            # il choisit de poser un mur et il y a assez de mur 
            if choix == "mur" and l1 > 0:

                # tant que le mur n'est pas pose, on recommence
                while True :

                    # on choisit une position legale
                    ((x1,y1),(x2,y2)) = draw_random_wall_location()

                    print(walls[0][i])
                    # on pose les murs en changeant leurs positions (a la position legale ci-dessus)
                    walls[0][i].set_rowcol(x1,y1)
                    walls[0][i+1].set_rowcol(x2,y2)

                    # dans la matrice, les murs aussi sont poses 
                    g[x1][y1]=False
                    g[x2][y2]=False

                    # on calcule le chemin pour le joueur 
                    pj0 = ProblemeGrid2D(initStates[0],objectifs[0],g,'manhattan')
                    path_j0 = probleme.astar(pj0,verbose=False)

                    # on calcule aussi le chemin pour le joueur adverse afin de voir si le mur posé bloque
                    p1_test = ProblemeGrid2D(initStates[1],objectifs[1],g,'manhattan')
                    path_j1_test = probleme.astar(p1_test,verbose=False)

                    print("Path après mur j0",path_j0)

                    # si le mur ne bloque pas l'acces a l'objectif, alors on pose !
                    if objectifs[0] in path_j0 and objectifs[1] in path_j1_test:                     
                        i = i + 2
                        l1 = l1 - 2
                        print("mur bien placé j0",i,l1)
                        game.mainiteration()
                        break

                    # sinon, on retire le mur et on recommence 
                    g[x1][y1]=True
                    g[x2][y2]=True


            else: # se déplace
                # on definit le chemin avec A*
                p = ProblemeGrid2D(initStates[0],objectifs[0],g,'manhattan')
                path_j0 = probleme.astar(p,verbose=False)
                print ("Chemin trouvé j0:", path_j0)

                # on avance
                row0,col0 = path_j0[1]
                posPlayers[0]=(row0,col0)
                players[0].set_rowcol(row0,col0)
                print ("pos joueur 0:", row0,col0)

                # on verifie si le joueur a atteint sa position
                if (row0,col0) == objectifs[0]:
                    print("le joueur 0 a atteint son but!")
                    break
                game.mainiteration()

        # le joueur j1 joue 
        else:
            # passage de main pour le tour suivant 
            j = "j0"

            choix = random.choice(jeu)
            # cas ou on pose un mur 
            if choix == "mur" and l2 > 0:
                while True :

                    # on pose un mur 
                    ((x1,y1),(x2,y2)) = draw_random_wall_location()
                    walls[1][k].set_rowcol(x1,y1)
                    walls[1][k+1].set_rowcol(x2,y2)
                    g[x1][y1]=False
                    g[x2][y2]=False

                    # on definit le chemin du joueur avec A*
                    p = ProblemeGrid2D(initStates[1],objectifs[1],g,'manhattan')
                    path_j2 = probleme.astar(p,verbose=False)
                    print("Path après mur j1",path_j2)

                    # on calcule aussi le chemin pour le joueur adverse afin de voir si le mur posé bloque
                    p0_test = ProblemeGrid2D(initStates[0],objectifs[0],g,'manhattan')
                    path_j0_test = probleme.astar(p0_test,verbose=False)

                    # si le mur ne bloque pas l'acces a l'objectif, alors on pose !
                    if objectifs[1] in path_j2 and objectifs[0] in path_j0_test: # and path de joueur 0                      
                        k = k + 2
                        l2 = l2 - 2
                        print("mur bien placé j1",k,l2)
                        game.mainiteration()
                        break

                    # sinon on retire le mur et on recommence 
                    g[x1][y1]=True
                    g[x2][y2]=True

            # sinon, j1 se deplace
            else:
                # chemin 
                p = ProblemeGrid2D(initStates[1],objectifs[1],g,'manhattan')
                path_j2 = probleme.astar(p,verbose=False)
                print ("Chemin trouvé j1:", path_j2)

                # deplacement du joueur 
                row1,col1 = path_j2[1]
                posPlayers[1]=(row1,col1)
                players[1].set_rowcol(row1,col1)
                print ("pos joueur 1:", row1,col1)

                # si j1 a atteint l'objectif 
                if (row1,col1) == objectifs[1]:
                    print("le joueur 1 a atteint son but!")
                    break
                game.mainiteration()
                
            
                    
                
                
    # #-------------------------------
    # Le joueur 0 place tous les murs au hasard
    #-------------------------------
                    
                     
    # for i in range(0,len(walls[0]),2): 
    #     ((x1,y1),(x2,y2)) = draw_random_wall_location()
    #     walls[0][i].set_rowcol(x1,y1)
    #     walls[0][i+1].set_rowcol(x2,y2)
    #     game.mainiteration()

   
    
    # #-------------------------------
    # # calcul A* pour le joueur 1
    # #-------------------------------
    

    
    # g =np.ones((nbLignes,nbCols),dtype=bool)  # une matrice remplie par defaut a True  
    # for w in wallStates(allWalls):            # on met False quand murs
    #     g[w]=False
    # for i in range(nbLignes):                 # on exclut aussi les bordures du plateau
    #     g[0][i]=False
    #     g[1][i]=False
    #     g[nbLignes-1][i]=False
    #     g[nbLignes-2][i]=False
    #     g[i][0]=False
    #     g[i][1]=False
    #     g[i][nbLignes-1]=False
    #     g[i][nbLignes-2]=False
    # p = ProblemeGrid2D(initStates[1],objectifs[1],g,'manhattan')
    # path = probleme.astar(p,verbose=False)
    # print ("Chemin trouvé:", path)
        
    
    #-------------------------------
    # Boucle principale de déplacements 
    #-------------------------------
    
            
    # posPlayers = initStates

    # for i in range(iterations):
        
    #     # on fait bouger le joueur 1 jusqu'à son but
    #     # en suivant le chemin trouve avec A* 
        
    #     row,col = path[i]
    #     posPlayers[1]=(row,col)
    #     players[1].set_rowcol(row,col)
    #     print ("pos joueur 1:", row,col)
    #     if (row,col) == objectifs[1]:
    #         print("le joueur 1 a atteint son but!")
    #         break
        
    #     # mise à jour du pleateau de jeu
    #     game.mainiteration()

                
        
            
    
    pygame.quit()
    
    
    
    
    #-------------------------------
    
        
    
    
   

if __name__ == '__main__':
    main()
    

