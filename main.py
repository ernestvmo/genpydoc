from extractor.extract import Extract

if __name__ == "__main__":
    e = Extract(["."])
    x = e.get_coverage()
    print(x)
