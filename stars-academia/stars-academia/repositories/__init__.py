from repositories.academia_repo import AcademiaRepositorio
from repositories.matricula_repo import CheckinRepositorio, MatriculaRepositorio
from repositories.plano_repo import PlanoRepositorio
from repositories.treino_repo import (ExercicioRepositorio, GrupoMuscularRepositorio, TreinoRealizadoRepositorio,
                                      TreinoRepositorio)
from repositories.usuario_repo import UsuarioRepositorio

__all__ = ["AcademiaRepositorio", "UsuarioRepositorio", "PlanoRepositorio", "MatriculaRepositorio",
           "CheckinRepositorio", "GrupoMuscularRepositorio", "ExercicioRepositorio", "TreinoRepositorio",
           "TreinoRealizadoRepositorio"]
