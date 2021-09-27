from autochit_bot import add_word

while True:
    try:
        inp = input()
    except EOFError:
        break
    else:
        en, fa, short = inp.split(',')
        add_word(en, fa, short in ('1', 'True', 'true'))
