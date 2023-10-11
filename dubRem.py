with open('verbs.txt') as result:
    uniqelines = set(result.readlines())
    with open('verbs.txt', 'w') as rmdup:
        rmdup.writelines(set(uniqlines))
