from app import create_app

# Cria a aplicação
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
