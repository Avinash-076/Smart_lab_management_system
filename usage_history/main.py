from process_filter import get_useful_applications


def main():

    applications = get_useful_applications()

    print("\nUseful Applications")
    print("====================")

    for application in applications:

        print(
            f"PID: {application['pid']} | "
            f"Process: {application['process_name']}"
        )


if __name__ == "__main__":
    main()