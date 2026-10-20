/* eslint-disable react/prop-types */
import React, { Component } from 'react';

import moment from 'moment';
import DatePicker from 'react-datepicker';
import { Portal } from 'react-overlays';
import { connect } from 'react-redux';

import BaseField from 'components/form-elements/BaseField';
import DateFormat from 'consts/dateFormat';
import { formatDate, getDateFormat, getLocaleCode } from 'utils/translation-utils';

import 'react-datepicker/dist/react-datepicker.css';

const CalendarContainer = ({ children }) => {
  const el = document.getElementById('root');

  return (
    <Portal container={el}>
      {children}
    </Portal>
  );
};

class DateField extends Component {
  constructor(props) {
    super(props);

    this.dateInput = null;
    this.renderInput = this.renderInput.bind(this);
  }

  renderInput({
    value, dateFormat = 'MM/DD/YYYY', timeFormat = 'HH:mm', className = '',
    arrowLeft, arrowUp, arrowRight, arrowDown, fieldRef, onTabPress, localizeDate,
    localizedDateFormat = DateFormat.COMMON, showLocalizedPlaceholder, ...attributes
  }) {
    const onChangeRaw = (e) => {
      // AERIS: a typed numeric date is day-first (31/03/2028, 31-03-2028, 31.3.28), as on DRC
      // delivery notes. Without this, the picker's loose parse against the display format
      // (DD/MMM/YYYY) silently turned 31/03/2028 into 31/Mar/2026.
      const numeric = /^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})\s*$/.exec(e.target.value || '');
      if (numeric) {
        const parsed = moment(`${numeric[1]}/${numeric[2]}/${numeric[3]}`, ['D/M/YYYY', 'D/M/YY'], true);
        if (parsed.isValid()) {
          e.preventDefault();
          if (this.dateInput) {
            this.dateInput.setState({ inputValue: e.target.value });
          }
          attributes.onChange(parsed.format(dateFormat));
          return;
        }
      }
      attributes.onChange(e.target.value);
    };

    const getPlaceholder = () => {
      if (localizeDate && showLocalizedPlaceholder) {
        return this.props.dateFormat(localizedDateFormat);
      }

      return attributes.placeholderText;
    };

    const getFormat = () => {
      if (localizeDate) {
        return this.props.dateFormat(localizedDateFormat);
      }

      return dateFormat;
    };

    const onChange = (date) => {
      const val = !date || typeof date === 'string' ? date : date.format(dateFormat);
      attributes.onChange(val);
    };

    const getLocale = () => {
      if (localizeDate) {
        return this.props.localeCode;
      }

      return null;
    };

    return (
      <div className="date-field">
        <DatePicker
          className={`form-control form-control-xs ${className}`}
          {...attributes}
          placeholderText={getPlaceholder()}
          selected={moment(value, dateFormat).isValid() ? moment(value, dateFormat) : null}
          highlightDates={[!moment(value, dateFormat).isValid()
            ? moment(new Date(), dateFormat) : {}]}
          onChange={(date) => onChange(date)}
          onChangeRaw={onChangeRaw}
          onSelect={() => {
            this.dateInput.setOpen(false);
          }}
          popperContainer={CalendarContainer}
          onKeyPress={(event) => {
            if (event.which === 13 /* Enter */) {
              event.preventDefault();
            }
          }}
          onKeyDown={(event) => {
            switch (event.keyCode) {
              case 37: /* arrow left */
                if (arrowLeft && arrowLeft()) {
                  event.preventDefault();
                  this.dateInput.cancelFocusInput();
                  this.dateInput.setOpen(false);
                }
                break;
              case 38: /* arrow up */
                if (arrowUp && arrowUp()) {
                  event.preventDefault();
                  this.dateInput.cancelFocusInput();
                  this.dateInput.setOpen(false);
                }
                break;
              case 39: /* arrow right */
                if (arrowRight && arrowRight()) {
                  event.preventDefault();
                  this.dateInput.cancelFocusInput();
                  this.dateInput.setOpen(false);
                }
                break;
              case 40: /* arrow down */
                if (arrowDown && arrowDown()) {
                  event.preventDefault();
                  this.dateInput.cancelFocusInput();
                  this.dateInput.setOpen(false);
                }
                break;
              case 9: /* Tab key */
                if (onTabPress) {
                  onTabPress(event);
                }
                break;
              default:
            }
          }}
          disabledKeyboardNavigation
          popperClassName="force-on-top"
          showYearDropdown
          scrollableYearDropdown
          dateFormat={getFormat()}
          locale={getLocale()}
          timeFormat={timeFormat}
          timeIntervals={15}
          yearDropdownItemNumber={3}
          utcOffset={0}
          ref={(el) => {
            this.dateInput = el;
            if (el && fieldRef) {
              fieldRef(el.input);
            }
          }}
        />
      </div>
    );
  }

  render() {
    return (
      <BaseField
        {...this.props}
        renderInput={this.renderInput}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  formatDate: formatDate(state.localize),
  dateFormat: getDateFormat(state.localize),
  localeCode: getLocaleCode(state.localize),
});

export default connect(mapStateToProps)(DateField);
