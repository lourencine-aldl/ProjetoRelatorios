# Abrir o projeto na web (pelo Cursor)

## Opção 1: Atalho — abrir a janela do navegador (recomendado)

Pressione **Ctrl+Shift+B** (ou Cmd+Shift+B no Mac).

A janela do Simple Browser abre dentro do Cursor com o projeto (http://127.0.0.1:8000/).

---

## Opção 2: Paleta de Comandos (Simple Browser)

1. Pressione **Ctrl+Shift+P** (ou Cmd+Shift+P no Mac) para abrir a Paleta de Comandos.
2. Digite: **Simple Browser: Show**
3. Selecione o comando e pressione Enter.
4. Cole esta URL e pressione Enter:
   ```
   http://127.0.0.1:8000/
   ```

O Cursor abre a página dentro do editor.

---

## Opção 3: Clicar no link

Com o servidor rodando, **Ctrl+clique** (ou Cmd+clique no Mac) no link abaixo para abrir no navegador padrão:

**http://127.0.0.1:8000/**

Outras páginas:
- [Login](http://127.0.0.1:8000/login/) — usuário: teste, senha: 123456
- [Dashboard](http://127.0.0.1:8000/dashboard/)
- [Admin](http://127.0.0.1:8000/admin/)

---

## Servidor não está rodando?

No terminal, dentro da pasta do projeto:

```bash
cd /home/Projetos/Projeto-Django
source .venv/bin/activate
python manage.py runserver
```

Depois use uma das opções acima.
