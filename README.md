# Point-cloud-processing
A suite of scripts and easy-to-follow tutorial to process point cloud data with Python, from scratch.
* [Point Cloud Basics](https://towardsdatascience.com/discover-3d-point-cloud-processing-with-python-6112d9ee38e7)

## Prerequisites

A computer with internet access, and (optionnally), a Gmail and GDrive account to make it work out of the box.

## Installing

Install the required visualization library before running the examples:

```bash
pip install open3d
```

## Documentation

Documentation of the various scripts can be found on the related articles: [Medium articles](https://medium.com/@florentpoux).

## Built With

* [Python](https://www.python.org/) - A cross-platform document-oriented database
* [NumPy](https://numpy.org/) - A Python library that add support for large, multi-dimensional arrays and matrices.
* [open3D](http://www.open3d.org/) - A Modern Python Library for 3D Data Processing
* [LasPy](https://laspy.readthedocs.io/en/latest/) - A Python library for reading, modifying and writing LAS files. 
* [Matplotlib](https://matplotlib.org/) - A library for creating static, animated, and interactive visualizations in Python.

## Loan Portfolio Visualization

The repository now includes a small example showing how point-cloud tools can visualize
loan portfolio metrics. The `loan_portfolio_visualizer.py` script reads a CSV file
containing `loanbalance`, `loanrate`, `loanaddedOrRemovedFlag`, and
`loantermOrAgeInMonths` columns. Each loan is mapped to a 3D point where:

* **X** = loan term or age in months
* **Y** = balance
* **Z** = interest rate

Points are colored green for newly added loans and red for loans that have been
removed. To try it out, run:

```bash
python CODE/loan_portfolio_visualizer.py DATA/loan_data_example.csv
```

This will open an interactive Open3D window displaying the loan portfolio.

## Acknowledgments

These tools are developed after my PhD, in order to try and support developers & researchers in their point cloud processing endavour, from scratch.

## Authors

* **Florent Poux** - *Idea and development* - [Linkedin](https://twitter.com/ga_nys)

This project is supported by the [3D Geodata Academy](https://learngeodata.eu), that provides 3D Courses around Photogrammetry, Point Cloud Processing, Semantic Segmentation, Classificaiton, Virtual Reality & more.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE) file for details.
