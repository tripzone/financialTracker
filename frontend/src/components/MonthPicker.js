import React, { Component } from 'react';
import request from 'request';
import classnames from 'classnames';
import { Dropdown, Button, Input } from 'react-materialize'

import './MonthPicker.css';


class MonthPicker extends Component {

	constructor(props) {
		super(props);
	}

	submitItemChange() {

	}

	render() {
		return (
			<div className="monthInput">
				<Input s={4} type='select' onChange={(x) => this.props.onSubmit(x.target.value)}>
					<option value="0">-</option>
					<option value="1">Jan</option>
					<option value="2">Feb</option>
					<option value="3">Mar</option>
					<option value="4">Apr</option>
					<option value="5">May</option>
					<option value="6">Jun</option>
					<option value="7">Jul</option>
					<option value="8">Aug</option>
					<option value="9">Sep</option>
					<option value="10">Oct</option>
					<option value="11">Nov</option>
					<option value="12">Dec</option>
				</Input>
			</div>
		);
	}
}

export default MonthPicker;
