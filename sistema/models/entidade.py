"""Classe base abstrata de todas as entidades do sistema."""
from abc import ABC, abstractmethod


class Entidade(ABC):
    """Toda entidade tem um id (gerado pelo banco) e sabe se validar.

    Conceitos de POO aplicados:
      - Abstração: não dá para instanciar Entidade diretamente.
      - Encapsulamento: o id fica em atributo protegido (_id) e só pode
        ser definido uma vez.
    """

    def __init__(self, id=None):
        self._id = id

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, valor):
        if self._id is not None and valor != self._id:
            raise ValueError("O id de uma entidade não pode ser alterado.")
        self._id = valor

    @property
    def eh_novo(self):
        """True enquanto o objeto ainda não foi salvo no banco."""
        return self._id is None

    @abstractmethod
    def validar(self):
        """Cada subclasse define suas próprias regras de validação."""

    def __eq__(self, outro):
        return (isinstance(outro, self.__class__)
                and self._id is not None
                and self._id == outro._id)

    def __hash__(self):
        return hash((self.__class__.__name__, self._id))

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self._id}>"
