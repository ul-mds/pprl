#!/bin/sh
if [ -z "$1" ]
then
    echo "usage: $0 project_name"
    exit 1
fi

PROJECT_NAME="$1"

DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}/.." || exit 2

mkdir -p "packages/$PROJECT_NAME"
cd "packages/$PROJECT_NAME" || exit 2

poetry init -n --name "$PROJECT_NAME" \
    --author "$(git config user.name) <$(git config user.email)>" \
    --python "^3.10" \
    --dev-dependency "pytest" \
    --dev-dependency "ruff" || exit 3

cat <<EOF >"poetry.toml"
[virtualenvs]
create = true
in-project = true
path = ".venv"
EOF

cat <<EOF >"README.md"
# $PROJECT_NAME
EOF

poetry install --no-root || exit 3

. "${DIR}"/projects.sh
PROJECTS_NEW=$(echo "$PROJECTS $PROJECT_NAME" | xargs)

cat <<EOF > "${DIR}/projects.sh"
#!/bin/sh
PROJECTS="$PROJECTS_NEW"
EOF
