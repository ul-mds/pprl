#! /bin/sh
if [ $# -eq 0 ]; then
    echo "usage: $0 poetry_arg0 [poetry_arg1 [...]]"
    exit 1
fi

DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}/.." || exit 2

. "$DIR/../scripts/projects.sh"

for PROJECT in $PROJECTS
do
    printf "\n=> %s\n\n" "$PROJECT"
    cd "$DIR/../packages/$PROJECT" || exit 2
    poetry "$@"
done
