#!/bin/bash

# Script avanzato per automatizzare git add, commit e push
# Inizializza automaticamente una repository Git se non esiste

set -e  # Exit immediatamente su errori

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Funzioni di logging
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_action() {
    echo -e "${PURPLE}🔧 $1${NC}"
}

# Inizializza repository Git se non esiste
initialize_git_repo() {
    log_action "Inizializzazione repository Git..."
    
    git init
    log_success "Repository Git inizializzata"
    
    # Configurazione branch principale
    git branch -M main
    log_info "Branch principale rinominato in 'main'"
    
    # Chiedi se aggiungere un remote origin
    echo ""
    log_info "Vuoi configurare un remote origin? (s/n)"
    read -r configure_remote
    
    if [[ "$configure_remote" =~ ^[Ss]$ ]]; then
        log_info "Inserisci l'URL del remote origin:"
        read -r remote_url
        
        if [ -n "$remote_url" ]; then
            git remote add origin "$remote_url"
            log_success "Remote origin aggiunto: $remote_url"
        else
            log_warning "Nessun URL fornito, salto configurazione remote"
        fi
    else
        log_info "Configurazione remote saltata"
    fi
    
    # Crea file .gitignore se non esiste
    if [ ! -f ".gitignore" ]; then
        log_action "Creazione file .gitignore base..."
        cat > .gitignore << 'EOF'
# File di sistema
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# File di IDE
.vscode/
.idea/
*.swp
*.swo

# File di log
*.log
logs/

# Dipendenze
node_modules/
vendor/
.env
.env.local
.env.production
EOF
        log_success "File .gitignore creato"
    fi
    
    return 0
}

# Verifica e inizializza repository Git se necessario
check_and_initialize_git() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_warning "Questa directory non è una repository Git!"
        echo ""
        log_info "Vuoi inizializzare una nuova repository Git qui? (s/n)"
        read -r initialize_repo
        
        if [[ "$initialize_repo" =~ ^[Ss]$ ]]; then
            initialize_git_repo
            return 1  # Ritorna 1 per indicare che è una nuova repo
        else
            log_error "Operazione annullata dall'utente"
            exit 1
        fi
    fi
    return 0  # Ritorna 0 se era già una repo
}

# Verifica connessione a remote
check_remote_connection() {
    local remote_url
    remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
    
    if [ -z "$remote_url" ]; then
        log_warning "Nessun remote 'origin' configurato"
        return 1
    fi
    
    if ! git ls-remote origin > /dev/null 2>&1; then
        log_error "Impossibile connettersi al remote origin: $remote_url"
        return 1
    fi
    
    return 0
}

# Ottieni branch corrente
get_current_branch() {
    git branch --show-current
}

# Risolvi conflitti preferendo file locali
resolve_conflicts_local() {
    log_info "Risoluzione conflitti preferendo file locali..."
    
    # Trova file in conflitto
    local conflicted_files
    conflicted_files=$(git diff --name-only --diff-filter=U)
    
    if [ -n "$conflicted_files" ]; then
        log_warning "File in conflitto:"
        echo "$conflicted_files"
        
        # Per ogni file in conflitto, usa la versione locale
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                log_info "Usando versione locale per: $file"
                git checkout --ours "$file"
                git add "$file"
            fi
        done <<< "$conflicted_files"
        
        log_success "Conflitti risolti con versione locale"
    else
        log_info "Nessun conflitto da risolvere"
    fi
}

# Pull con strategia preferenza locale
safe_pull() {
    local current_branch="$1"
    
    log_info "Eseguendo pull con preferenza file locali..."
    
    # Prova pull con strategia ours
    if git pull -X ours origin "$current_branch" 2>/dev/null; then
        log_success "Pull completato con successo"
        return 0
    fi
    
    # Se fallisce, gestisci manualmente i conflitti
    log_warning "Pull automatico fallito, risolvendo conflitti manualmente..."
    
    # Fai il merge manualmente
    if git fetch origin && git merge --no-commit origin/"$current_branch"; then
        resolve_conflicts_local
        git commit -m "Merge con preferenza file locali"
        return 0
    else
        resolve_conflicts_local
        if git commit -m "Merge con preferenza file locali" 2>/dev/null; then
            log_success "Merge completato con successo"
            return 0
        fi
    fi
    
    return 1
}

# Gestione prima commit per nuova repository
handle_first_commit() {
    log_action "Preparazione primo commit..."
    
    # Verifica se ci sono file da commitare
    if [ -z "$(git status --porcelain)" ]; then
        log_warning "Nessun file da commitare nella nuova repository!"
        log_info "Aggiungi alcuni file alla directory prima di continuare"
        exit 0
    fi
    
    # Mostra stato
    log_info "File rilevati per il primo commit:"
    git status --short
    
    # Git add di tutti i file
    echo ""
    log_info "Aggiungendo tutti i file..."
    git add .
    
    return 0
}

# Main script
main() {
    echo -e "${BLUE}=== Git Auto Commit & Push (Sicuro) ===${NC}"
    echo ""
    
    # Verifica e inizializza repository Git se necessario
    local is_new_repo=0
    if ! check_and_initialize_git; then
        is_new_repo=1
        log_success "Nuova repository Git inizializzata!"
    fi
    
    local current_branch
    current_branch=$(get_current_branch)
    log_info "Branch corrente: $current_branch"
    
    # Gestione prima commit per nuove repository
    if [ $is_new_repo -eq 1 ]; then
        handle_first_commit
    fi
    
    # Verifica stato repository
    if [ -z "$(git status --porcelain)" ]; then
        log_info "Nessuna modifica da committare!"
        exit 0
    fi
    
    # Mostra modifiche
    log_info "File modificati:"
    git status --short
    
    # Git add di tutti i file
    echo ""
    log_info "Aggiungendo tutti i file..."
    git add .
    
    # Verifica se ci sono modifiche da committare dopo l'add
    if git diff --cached --quiet; then
        log_info "Nessuna modifica da committare dopo git add!"
        exit 0
    fi
    
    # Richiedi il messaggio di commit
    echo ""
    log_info "Inserisci il messaggio del commit:"
    read -r commit_message
    
    # Verifica che il messaggio non sia vuoto
    if [ -z "$commit_message" ]; then
        log_error "Il messaggio del commit non può essere vuoto!"
        exit 1
    fi
    
    # Esegui il commit
    echo ""
    log_info "Eseguendo commit..."
    if ! git commit -m "$commit_message"; then
        log_error "Fallito il commit!"
        exit 1
    fi
    
    log_success "Commit creato con successo!"
    
    # Gestione del push
    if check_remote_connection; then
        echo ""
        log_info "Controllo aggiornamenti dal remote..."
        
        # Prova a fare pull prima del push (solo se non è il primo commit di una nuova repo)
        if [ $is_new_repo -eq 0 ] && safe_pull "$current_branch"; then
            log_success "Aggiornamento dal remote completato"
        elif [ $is_new_repo -eq 0 ]; then
            log_warning "Problemi durante l'aggiornamento, continuando con il push..."
        fi
        
        # Esegui il push
        echo ""
        log_info "Eseguendo push su origin $current_branch..."
        
        if git push origin "$current_branch"; then
            log_success "Push completato con successo!"
        else
            # Se il push fallisce, prova con --set-upstream per nuove repository
            if [ $is_new_repo -eq 1 ]; then
                log_info "Tentativo push con --set-upstream..."
                if git push --set-upstream origin "$current_branch"; then
                    log_success "Push e setup upstream completati con successo!"
                else
                    log_error "Push fallito!"
                    exit 1
                fi
            else
                log_error "Push fallito!"
                log_info "Prova con: git push --force-with-lease origin $current_branch"
                exit 1
            fi
        fi
    else
        log_warning "Push non eseguito (nessuna connessione al remote)"
    fi
    
    # Stato finale
    echo ""
    log_success "Operazioni completate!"
    log_info "Stato finale:"
    git status --short
}

# Gestione interrupt
trap 'log_error "Script interrotto dall'\''utente"; exit 1' INT TERM

# Esegui main function
main "$@"